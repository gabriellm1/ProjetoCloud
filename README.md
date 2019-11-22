# ProjetoCloud
### Gabriel Monteiro

## Introdução a aplicação

  Foi utilizado uma base de dados mongo em conexão com um WebServer em Node.js . Esse WebServer foi reaproveitado de um backend de um app que eu desenvolvi. O app, por mais que fosse para outra aplicação, era inspirado no app da yellow, então na base de dados desse projeto será encontrado "markers", que são objetos com nome e a localização do usuário(latitude,longitude). Com fins de focar apenas na parte da infraestrutura, o WebServer faz uso apenas das partes dos markers e nela não diferencia inserções iguias, então todo POST incluirá uma collection diferente sempre(criando um novo index). Dessa forma o PUT e o DELETE terão um comportamento específico que está explicado nas instruções. Os WebServers que rodam na instância intermediadora e nas instâncias do auto scale são servidores Flask que recebem um request e refaz outro.

## Instruções

 - Colocar a key a ser importada no diretório raiz com o nome de id_rsa.pub
 
 - Rodar o script `python3 script_B.py`
 
 - Café
 
 - Após ter rodado o script, o arquivo client já deve possuir o DNS do load balancer nele
   - Caso queira alterar o endereço do load balancer, alterar na variável server_addr
   
 - Com o arquivo client pronto, testar o CRUD no terminal com:
 
    - `./client listar` : (GET) Irá listar todos os markers na base de dados 
    - `./client adicionar` : (POST) Irá adicionar um marker na base de dados, sendo seu conteúdo dentro do arquivo post_or_put.json 
    - `./client atualizar` : (PUT) Irá atualizar um marker existente na base de dados, sendo seu conteúdo dentro do arquivo post_or_put.json.  Obs: Se tiver 2 ou mais iguais irá atualizar o mais antigo adicionado/ou alterado. Se não houver o marker na base de dados, trará a resposta {"existence": false} 
    - `./client apagar` : (DELETE) Irá deletar um marker existente na base de dados, sendo seu conteúdo dentro do arquivo del.json. Obs: Se tiver 2 ou mais iguais irá deletar o mais antigo adicionado/ou alterado e retornar {'marker':'deleted'}. Se não houver o marker na base de dados, trará a resposta {"existence": false} 
