# SentinelLab

Ferramenta educacional de monitoramento da integridade de arquivos. O projeto combina C e Python para calcular hashes SHA-256, comparar arquivos com uma baseline e registrar alterações em JSONL.

## Funcionalidades

- Cálculo de SHA-256 em Python para um arquivo individual.
- Motor de hash em C usando a interface EVP do OpenSSL.
- Inventário JSON com caminhos relativos dos arquivos monitorados.
- Detecção de arquivos novos, modificados e removidos.
- Registro de eventos com data e fuso horário em JSONL.
- Testes automatizados para comparação, inventário e integração Python/C.

## Estrutura

```text
sentinellab/
|-- c_engine/
|   `-- hashfile.c
|-- Dockerfile
|-- .dockerignore
|-- data/
|-- lab/
|   |-- config.txt
|   `-- exemplo.txt
|-- python/
|   |-- c_hash.py
|   |-- detect_changes.py
|   |-- hash_file.py
|   |-- inventory.py
|   |-- menu.py
|   `-- web_app.py
|-- render.yaml
|-- reports/
|-- tests/
|   `-- test_integrity.py
|-- .gitignore
`-- README.md
```

`data/inventario.json`, `reports/eventos.jsonl` e o executável compilado são arquivos locais gerados durante o uso e estão ignorados pelo Git.

## Requisitos

- Python 3
- GCC
- OpenSSL compatível com a toolchain do GCC, incluindo os headers de desenvolvimento

No Windows, MSYS2 UCRT64 é uma opção para instalar GCC e OpenSSL. Instale pacotes compatíveis com o mesmo ambiente UCRT64 e execute os comandos a seguir em seu terminal UCRT64, na raiz do projeto.

No terminal MSYS2 UCRT64, os pacotes podem ser instalados com:

```sh
pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-openssl
```

## Compilar o motor C

```sh
gcc c_engine/hashfile.c -o c_engine/hashfile.exe -static -lcrypto -lbcrypt -lws2_32 -lcrypt32
```

O diretório `c_engine/` deve conter o `hashfile.exe` compilado antes de usar o inventário, o detector ou a ponte Python/C. O executável não é incluído no repositório; compile-o para sua plataforma.

## Como usar

Execute os comandos a partir da raiz do projeto.

### Abrir o menu interativo

```sh
python python/menu.py
```

O menu permite calcular o hash de um arquivo pelo motor C, criar uma baseline, detectar alterações ou executar os testes. Atualizar a baseline exige digitar `ATUALIZAR` para confirmar, pois essa ação substitui a referência existente.

### Abrir a interface no navegador

```sh
python python/web_app.py
```

O servidor local abre `http://127.0.0.1:8765/` no navegador. Ele escuta somente no computador local. A interface permite calcular hashes de arquivos dentro de `lab/`, atualizar a baseline com confirmação, detectar alterações e executar os testes.

### Hospedar uma demonstração pública e incorporar no Google Sites

O Google Sites não executa Python nem o motor C. Para publicar uma demonstração interativa, hospede o backend separadamente e incorpore sua URL no Google Sites. Este projeto inclui um `Dockerfile` e uma configuração `render.yaml` para facilitar a publicação como serviço Docker no Render.

1. Publique o código-fonte em um repositório GitHub seu. Não envie credenciais, logs pessoais nem inventários locais.
2. No Render, crie um serviço usando esse repositório e o arquivo `render.yaml`. O plano gratuito pode suspender o serviço quando estiver inativo; a primeira abertura pode demorar.
3. Aguarde o deploy e teste `https://SUA-URL.onrender.com/health`. A resposta esperada é `{"status":"ok"}`.
4. No Google Sites, escolha **Inserir → Incorporar → URL**, informe a URL pública do serviço e ajuste o tamanho do quadro.

O modo hospedado é somente leitura: a baseline é criada durante o build, não pode ser atualizada pela interface e as verificações não gravam logs. Isso evita que visitantes substituam a referência ou produzam eventos persistentes. O plano gratuito pode reiniciar o container e seus arquivos locais; portanto, essa demonstração não oferece histórico persistente nem deve ser usada para monitorar dados reais. Para um monitoramento real, mantenha o SentinelLab em um ambiente privado e controlado.

### Calcular um hash com a implementação Python

```sh
python python/hash_file.py
```

Esse comando calcula o hash SHA-256 de `lab/config.txt` sem depender do executável C.

### Calcular um hash usando o motor C

```sh
python python/c_hash.py lab/config.txt
```

Sem argumento, `c_hash.py` usa `lab/config.txt`. Também é possível passar o caminho de outro arquivo:

```sh
python python/c_hash.py lab/exemplo.txt
```

### Criar ou atualizar a baseline

```sh
python python/inventory.py
```

Isso grava os hashes atuais da pasta `lab/` em `data/inventario.json`, substituindo qualquer baseline anterior. Execute apenas quando quiser estabelecer ou atualizar conscientemente a referência de confiança.

### Detectar alterações

```sh
python python/detect_changes.py
```

O detector compara o estado atual de `lab/` com a baseline, mostra eventos `NOVO`, `MODIFICADO` e `REMOVIDO`, e acrescenta os eventos a `reports/eventos.jsonl`. Ele não atualiza a baseline. Por isso, verificações repetidas podem registrar novamente as mesmas alterações.

### Executar os testes

```sh
python -m unittest discover -s tests -v
```

Os testes automatizados não exigem OpenSSL nem um executável compilado: a chamada externa do motor C é simulada nos testes.

## Formatos de dados

- `data/inventario.json`: objeto JSON que associa cada caminho relativo em `lab/` ao seu hash SHA-256.
- `reports/eventos.jsonl`: um objeto JSON por linha, contendo o tipo do evento, o caminho do arquivo e a data/hora com fuso horário.

## Limitações de segurança

Este projeto é destinado ao aprendizado e não é um produto de segurança pronto para produção.

- Uma alteração detectada pode ser legítima e não prova, por si só, que houve um ataque.
- Se um agente puder modificar os arquivos monitorados e a baseline, também poderá comprometer a comparação.
- Os logs locais podem ser alterados ou removidos por quem tiver permissão suficiente no sistema.
- A baseline só muda quando `inventory.py` é executado, mas o arquivo JSON não tem proteção criptográfica ou controle de acesso próprio.
- O detector não identifica a causa nem o autor de uma alteração e pode registrar o mesmo evento em verificações sucessivas.

Para uso real, proteja a baseline e os logs com controles de acesso adequados e considere armazená-los em um sistema separado.

## Publicação no GitHub

O repositório deve incluir o código-fonte, os testes e esta documentação. O executável, o inventário local e o log de eventos estão excluídos pelo `.gitignore`. Depois de inicializar o Git e criar um repositório vazio no GitHub, configure o remoto e publique a branch principal:

```sh
git init
git add .
git commit -m "Initial SentinelLab implementation"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/SentinelLab.git
git push -u origin main
```

Se o repositório já tiver um remoto chamado `origin`, confira sua configuração antes de adicioná-lo novamente.

## Finalidade

Projeto de estudo para praticar C, Python, SHA-256, integração entre processos, testes automatizados e conceitos defensivos de monitoramento de integridade.
