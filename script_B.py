import boto3
from boto.ec2 import *
import time
import fileinput
import os
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale import LaunchConfiguration
from boto.ec2.autoscale import AutoScalingGroup
from boto.ec2.autoscale import ScalingPolicy


ec2 = boto3.client('ec2', region_name='us-east-2')
ec2_virginia = boto3.client('ec2', region_name='us-east-1')
lb_client = boto3.client('elb',region_name='us-east-1')
autoscalling = boto3.client('autoscaling', region_name='us-east-1')

# Delete and Create a new KeyPair(Importing publickey)
try:
    ec2.delete_key_pair(KeyName='gabriel')
    print("Deletando KeyPair\n")
except Exception as e:
    print("KeyPair não existente\n")

key_file = open('id_rsa.pub','r')
pub_key = key_file.read()

response = ec2.import_key_pair(
    KeyName='gabriel',
    PublicKeyMaterial=pub_key.encode('ASCII')
)
print("KeyPair 'gabriel' criado\n")


# gets instances and terminates them
response = ec2_virginia.describe_instances(
Filters=[{'Name': 'tag:WebServerInter','Values': ['Gabriel']},])    
for reservation in response['Reservations']:
    for instance_description in reservation['Instances']:
        instance_id = instance_description['InstanceId']
        if instance_description['State']['Name'] != 'terminated':
            inter_instance_ip = instance_description['PublicIpAddress']
        ec2_virginia.terminate_instances(InstanceIds=[instance_id], DryRun=False)
        waiter = ec2_virginia.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=[instance_id])
print("Removendo Instância Intermediadora\n")

response = ec2_virginia.describe_instances(
Filters=[{'Name': 'tag:WebServer','Values': ['Gabriel']},])    
for reservation in response['Reservations']:
    for instance_description in reservation['Instances']:
        instance_id = instance_description['InstanceId']
        if instance_description['State']['Name'] != 'terminated':
            instance_ip = instance_description['PublicIpAddress']
        ec2_virginia.terminate_instances(InstanceIds=[instance_id], DryRun=False)
        waiter = ec2_virginia.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=[instance_id])
print("Removendo Instâncias do Webserver do AutoScale\n")

try:
    elastic_ip = ec2_virginia.describe_addresses(PublicIps=[inter_instance_ip])
    alloc_id_del = elastic_ip['Addresses'][0]['AllocationId']
    response = ec2_virginia.release_address(AllocationId=alloc_id_del)
    print("Release no elastic IP da instância intermediadora\n")
except Exception as e:
    print(e)

allocation = ec2_virginia.allocate_address(Domain='vpn')
wsinter_alloc_ip = allocation['PublicIp']
wsinter_alloc_id = allocation['AllocationId']
print("Alocando elastic IP para instância intermediadora\n")

# gets instances and terminates them
response = ec2.describe_instances(
Filters=[{'Name': 'tag:WSMongo','Values': ['Gabriel']},])    
for reservation in response['Reservations']:
    for instance_description in reservation['Instances']:
        instance_id = instance_description['InstanceId']
        if instance_description['State']['Name'] != 'terminated':
            wsmongo_instance_ip = instance_description['PublicIpAddress']
        ec2.terminate_instances(InstanceIds=[instance_id], DryRun=False)
        waiter = ec2.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=[instance_id])

# gets instances and terminates them
response = ec2.describe_instances(
Filters=[{'Name': 'tag:Mongo','Values': ['Gabriel']},])    
for reservation in response['Reservations']:
    for instance_description in reservation['Instances']:
        instance_id = instance_description['InstanceId']
        if instance_description['State']['Name'] != 'terminated':
            mongo_instance_ip = instance_description['PublicIpAddress']
        ec2.terminate_instances(InstanceIds=[instance_id], DryRun=False)
        waiter = ec2.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=[instance_id])
print("Removendo Base de Dados\n")

# delete security group
try:
    response = ec2.describe_security_groups(GroupNames=['WSM'])
    for sg in response["SecurityGroups"]:
        ec2.delete_security_group(GroupName=sg['GroupName'])
    print("Deletando security group de acesso a WebServerMongo\n")
    response = ec2.describe_security_groups(GroupNames=['Database'])
    for sg in response["SecurityGroups"]:
        ec2.delete_security_group(GroupName=sg['GroupName'])
    print("Deletando security group de acesso a base de dados Mongo\n")
except Exception as e:
    print(e)

# create security group
sg = ec2.create_security_group(GroupName='WSM',Description='mongo')
ec2.authorize_security_group_ingress(GroupId=sg['GroupId'],IpPermissions=[
    {'IpProtocol': 'tcp',
    'FromPort': 22,
    'ToPort': 22,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
    {'IpProtocol': 'tcp',
    'FromPort': 443,
    'ToPort': 443,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
    {'IpProtocol': 'tcp',
    'FromPort': 4444,
    'ToPort': 4444,
    'IpRanges': [{'CidrIp': wsinter_alloc_ip+'/32'}]},
])
print("Security Group da instância de acesso a base de dados criado\n")


try:
    elastic_ip = ec2.describe_addresses(PublicIps=[mongo_instance_ip])
    alloc_id_del = elastic_ip['Addresses'][0]['AllocationId']
    response = ec2.release_address(AllocationId=alloc_id_del)
    print("Release no elastic IP da base de dados\n")
    elastic_ip = ec2.describe_addresses(PublicIps=[wsmongo_instance_ip])
    alloc_id_del = elastic_ip['Addresses'][0]['AllocationId']
    response = ec2.release_address(AllocationId=alloc_id_del)
    print("Release no elastic IP da instância de acesso a base de dados\n")
except Exception as e:
    print(e)

allocation = ec2.allocate_address(Domain='vpn')
mongo_alloc_ip = allocation['PublicIp']
mongo_alloc_id = allocation['AllocationId']
print("Alocando elastic IP para base de dados\n")

allocation = ec2.allocate_address(Domain='vpn')
wsmongo_alloc_ip = allocation['PublicIp']
wsmongo_alloc_id = allocation['AllocationId']
print("Alocando elastic IP para instância de acesso a base de dados\n")

# create security group
sg = ec2.create_security_group(GroupName='Database',Description='mongo')
ec2.authorize_security_group_ingress(GroupId=sg['GroupId'],IpPermissions=[
    {'IpProtocol': 'tcp',
    'FromPort': 22,
    'ToPort': 22,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
    {'IpProtocol': 'tcp',
    'FromPort': 27017,
    'ToPort': 27017,
    'IpRanges': [{'CidrIp': wsmongo_alloc_ip+'/32'}]},
])
print("Security Group da base de dados criado\n")




# create instance
response = ec2.run_instances(
    ImageId='ami-0d5d9d301c853a04a',
    InstanceType= "t2.micro",
    MinCount=1,
    MaxCount=1,
    KeyName='gabriel',
    SecurityGroups=['Database'],
    UserData='''#!/bin/bash
sudo apt-get update
sudo apt install mongodb -y
sudo mkdir -p /home/ubuntu/data/db
sudo chmod 777 /home/ubuntu/data/db
cd /home/ubuntu
sudo /etc/init.d/mongodb stop
sudo mongod --bind_ip_all --dbpath .
            ''',
    TagSpecifications=[{'ResourceType': 'instance','Tags': [{'Key': 'Mongo','Value': 'Gabriel'}]}]
)
print("Instância da base de dados criada\n")

# allocate elastic ip 
waiter = ec2.get_waiter('instance_status_ok')

inst_id = response['Instances'][0]['InstanceId']
private_ip_mongo = response['Instances'][0]['PrivateIpAddress']

waiter.wait(InstanceIds=[inst_id])


response = ec2.associate_address(AllocationId=mongo_alloc_id,
                                    InstanceId=inst_id)
print("IP associado a base de dados\n")


# create instance
response = ec2.run_instances(
    ImageId='ami-0d5d9d301c853a04a',
    InstanceType= "t2.micro",
    MinCount=1,
    MaxCount=1,
    KeyName='gabriel',
    SecurityGroups=['WSM'],
    UserData='''#!/bin/bash
sudo apt-get update
sudo apt install npm -y
cd /home/ubuntu
git clone https://github.com/gabriellm1/Zipa_Backend.git
cd Zipa_Backend
sudo chmod -R 777 src
cd src
sed 's@x:27@'''+mongo_alloc_ip+''':27@ ' index.js > n_index.js && sudo mv n_index.js index.js
cd ..
sudo cp node.service /etc/systemd/system
sudo systemctl enable node.service
sudo systemctl start node.service
            ''',
    TagSpecifications=[{'ResourceType': 'instance','Tags': [{'Key': 'WSMongo','Value': 'Gabriel'}]}]
)

print("Instância de acesso a base de dados criada\n")

# allocate elastic ip 
waiter = ec2.get_waiter('instance_status_ok')

inst_id = response['Instances'][0]['InstanceId']

waiter.wait(InstanceIds=[inst_id])


response = ec2.associate_address(AllocationId=wsmongo_alloc_id,
                                    InstanceId=inst_id)

print("IP associado a instância de acesso a base de dados\n")

time.sleep(30)


response = ec2.reboot_instances(InstanceIds=[inst_id])
print("Reboot na instância de acesso\n")

waiter = ec2.get_waiter('instance_status_ok')

waiter.wait(InstanceIds=[inst_id])




try:
    response = autoscalling.delete_auto_scaling_group(
        AutoScalingGroupName='AT-SCALE',
        ForceDelete=True
    )
    time.sleep(240)
    print("AutoScalling Group deletado\n")
except Exception as e:
    print(e)



try:
    response = autoscalling.delete_launch_configuration(
    LaunchConfigurationName='launch-proj'
    )
    print("Launch Config deletado\n")
except Exception as e:
    print(e)




# delete webserver image
try:
    image = ec2_virginia.describe_images(Filters=[{'Name': 'name','Values': ['WebServer']}])
    ec2_virginia.deregister_image(ImageId=image['Images'][0]['ImageId'])
    print("Imagem do webserver deletada\n")
except Exception as e:
    print(e)

# delete security group
try:
    response = ec2_virginia.describe_security_groups(GroupNames=['WS'])
    for sg in response["SecurityGroups"]:
        ec2_virginia.delete_security_group(GroupName=sg['GroupName'])
    print("Security Group do webserver deletado\n")
except Exception as e:
    print(e)

# create security group
sg = ec2_virginia.create_security_group(GroupName='WS',Description='server')
ec2_virginia.authorize_security_group_ingress(GroupId=sg['GroupId'],IpPermissions=[
    {'IpProtocol': 'tcp',
    'FromPort': 5000,
    'ToPort': 5000,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
    {'IpProtocol': 'tcp',
    'FromPort': 22,
    'ToPort': 22,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
])
print("Security Group do webserver criado\n")


ip_ohio = wsmongo_alloc_ip + ":4444"

# create instance
response = ec2_virginia.run_instances(
    ImageId='ami-04b9e92b5572fa0d1',
    InstanceType= "t2.micro",
    MinCount=1,
    MaxCount=1,
    KeyName='gabriel',
    SecurityGroups=['WS'],
    UserData='''#!/bin/bash
cd /home/ubuntu
sudo apt update
sudo apt install python3-flask -y
sudo git clone https://github.com/gabriellm1/Flask_Redir.git
cd Flask_Redir
sed 's@#end@"{}"@ ' flask_redir.py > n_flask.py && sudo mv n_flask.py flask_redir.py
cd /etc
sudo mkdir init
cd init
sudo cp /home/ubuntu/Flask_Redir/config_inter/flask.conf .
cd /lib/systemd/system
sudo cp /home/ubuntu/Flask_Redir/config_inter/flask.service .
sudo systemctl enable flask.service > /home/ubuntu/log.txt
sudo systemctl start flask.service > /home/ubuntu/log.txt
            '''.format(ip_ohio),
    TagSpecifications=[{'ResourceType': 'instance','Tags': [{'Key': 'WebServerInter','Value': 'Gabriel'}]}]
)
print("Instância intermediadora criada\n")

# allocate elastic ip 
waiter = ec2_virginia.get_waiter('instance_status_ok')

inst_id = response['Instances'][0]['InstanceId']

waiter.wait(InstanceIds=[inst_id])
response = ec2_virginia.associate_address(AllocationId=wsinter_alloc_id,
                                    InstanceId=inst_id)

print("IP associado a instância intermediadroa\n")

ip_intermed = wsinter_alloc_ip + ":5000"

# create instance
response = ec2_virginia.run_instances(
    ImageId='ami-04b9e92b5572fa0d1',
    InstanceType= "t2.micro",
    MinCount=1,
    MaxCount=1,
    KeyName='gabriel',
    SecurityGroups=['WS'],
    UserData='''#!/bin/bash
cd /home/ubuntu
sudo apt update
sudo apt install python3-flask -y
sudo git clone https://github.com/gabriellm1/Flask_Redir.git
cd Flask_Redir
sed 's@#end@"{}"@ ' flask_redir_auto.py > n_flask.py && sudo mv n_flask.py flask_redir_auto.py
cd /etc
sudo mkdir init
cd init
sudo cp /home/ubuntu/Flask_Redir/config_auto/flask.conf .
cd /lib/systemd/system
sudo cp /home/ubuntu/Flask_Redir/config_auto/flask.service .
sudo systemctl enable flask.service > /home/ubuntu/log.txt
sudo systemctl start flask.service > /home/ubuntu/log.txt
            '''.format(ip_intermed),
    TagSpecifications=[{'ResourceType': 'instance','Tags': [{'Key': 'WebServer','Value': 'Gabriel'}]}]
)
print("Subindo intância que será imagem do webserver\n")

waiter = ec2_virginia.get_waiter('instance_status_ok')

inst_id = response['Instances'][0]['InstanceId']

waiter.wait(InstanceIds=[inst_id])

# create webserver image
response = ec2_virginia.create_image(Name='WebServer',Description='WebserverAuto',InstanceId=inst_id)

image_id = response['ImageId']
image = ec2_virginia.describe_images(ImageIds=[image_id])
while image['Images'][0]['State'] == 'pending':
    time.sleep(5)
    image = ec2_virginia.describe_images(ImageIds=[image_id])
if image['Images'][0]['State'] == 'available':
    print("Imagem de webserver criada\n")
else:
    print("erro ao criar imagem")


# gets instances and terminates them
response = ec2_virginia.describe_instances(
Filters=[{'Name': 'tag:WebServer','Values': ['Gabriel']},])    
for reservation in response['Reservations']:
    for instance_description in reservation['Instances']:
        instance_id = instance_description['InstanceId']
        if instance_description['State']['Name'] != 'terminated':
            instance_ip = instance_description['PublicIpAddress']
        ec2_virginia.terminate_instances(InstanceIds=[instance_id], DryRun=False)
        waiter = ec2_virginia.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=[instance_id])
print("Instância base para imagem deletada\n")
# delete load balancer
try:
    response = lb_client.delete_load_balancer(LoadBalancerName='load-balancer')
    print("LoadBalancer deletado\n")
except Exception as e:
    print('erro')
    print(e)

# config and create load balancer


lb = lb_client.create_load_balancer(LoadBalancerName='load-balancer', 
                Listeners=[{'Protocol': 'tcp','LoadBalancerPort': 8080,'InstanceProtocol':'tcp','InstancePort': 5000}],
                AvailabilityZones=['us-east-1a', 'us-east-1b','us-east-1c','us-east-1d','us-east-1e','us-east-1f'])
print("LoadBalancer criado\n")
response = lb_client.configure_health_check(
    HealthCheck={
        'HealthyThreshold': 2,
        'Interval': 10,
        'Target': 'HTTP:5000/healthcheck',
        'Timeout': 3,
        'UnhealthyThreshold': 2,
    },
    LoadBalancerName='load-balancer',
)
print("Healthcheck configurado\n")
response = autoscalling.create_launch_configuration(
    LaunchConfigurationName='launch-proj',
    ImageId=image_id,
    InstanceType="t2.micro",
    KeyName='gabriel',
    SecurityGroups=[
        'WS',
    ],
    UserData='''#!/bin/bash
sudo service flask start > /home/ubuntu/log.txt
'''
)
print("Launch Configuration criado\n")
response = autoscalling.create_auto_scaling_group(
    AutoScalingGroupName='AT-SCALE',
    LaunchConfigurationName='launch-proj',
    MinSize=1,
    MaxSize=3,
    LoadBalancerNames=[
        'load-balancer',
    ],
    AvailabilityZones=['us-east-1a', 'us-east-1b'],
    Tags=[
        {
            'Key': 'ATSC',
            'Value': 'gabriel'
        },
    ]
)
print("AutoScalling Group criado\n")

print("Aplicação client pode acessar o DNS: {}".format(lb['DNSName']))

# colocando LoadBalancer client
with fileinput.FileInput("client", inplace=True) as file:
    for line in file:
        print(line.replace("dns_lb", lb['DNSName']), end='')