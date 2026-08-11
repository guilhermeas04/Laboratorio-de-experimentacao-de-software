# Lab 01 - Repositorios populares + Setup do Kanban

Este diretorio concentra os artefatos do Lab01. O objetivo deste README e padronizar como o grupo deve criar codigo, dados, validacoes e respostas das RQs para que todas as entregas sigam o mesmo formato.

## Estrutura do laboratorio

- `01 - LABORATORIO 01 - Repositorios populares + Setup do Kanban.md`: enunciado original do laboratorio.
- `code/`: scripts de coleta, consulta GraphQL, validacao, analise e exportacao.
- `data/`: arquivos de dados gerados pelos scripts.
- `docs/`: documentacao do processo, GitHub Projects, Kanban, WIP e RQs.
- `reports/`: respostas das RQs e relatorio final.

## Estrutura do codigo

Todo codigo da coleta e analise deve ficar em `lab1/code/src/`.

- `main.py`: ponto de entrada da coleta principal da sprint atual.
- `config.py`: leitura de variaveis de ambiente.
- `github_client.py`: cliente HTTP para executar queries GraphQL no GitHub.
- `queries/`: queries GraphQL usadas nas issues.
- `collectors/`: scripts que coletam e normalizam dados da API.
- `validators/`: validacoes rapidas por conjunto de RQs.
- `analyzers/`: scripts que calculam metricas e geram respostas em Markdown.
- `exporters/`: exportacao de CSVs e snapshots.

## Estrutura dos dados

- `data/raw/`: respostas brutas da API, quando necessario.
- `data/processed/`: CSVs tratados e prontos para analise.
- `data/snapshots/`: snapshots do GitHub Projects ao final de cada sprint.

Arquivos gerados em `data/` nao entram automaticamente no Git, exceto quando forem parte explicita da entrega. Os `.gitkeep` devem permanecer para manter as pastas versionadas.

## Configuracao local

Crie um arquivo local em `lab1/code/.env` usando `lab1/code/.env.example` como modelo.

```env
GITHUB_TOKEN=seu_token_aqui
GITHUB_GRAPHQL_URL=https://api.github.com/graphql
GITHUB_TOP_REPOSITORIES_LIMIT=100
```

Nunca commitar `.env` com token real.

## Padrao por issue

Cada issue deve entregar, quando aplicavel:

- uma query GraphQL especifica em `code/src/queries/`;
- uma funcao de coleta ou normalizacao em `code/src/collectors/`;
- uma validacao rapida em `code/src/validators/`;
- um script de analise em `code/src/analyzers/`;
- um CSV em `data/processed/`, se a entrega exigir dados;
- uma resposta em Markdown em `reports/`;
- commit referenciando o numero da issue.

Exemplo de commit:

```text
#11 implementa extracao das metricas RQ01 e RQ02
```

## Padrao para queries GraphQL

Cada query deve ter um nome claro e ficar em `code/src/queries/`.

Nome sugerido:

```text
rqXX_rqYY_repositories.graphql
```

Exemplos:

- `rq01_rq02_repositories.graphql`
- `rq03_rq04_repositories.graphql`
- `rq05_rq06_repositories.graphql`

As queries devem buscar apenas os campos necessarios para a issue. Isso reduz erro de API e deixa a validacao mais simples.

## Padrao para CSVs

Cada CSV tratado deve ficar em `data/processed/`.

Nome sugerido:

```text
rqXX_rqYY.csv
```

Exemplos:

- `rq01_rq02.csv`
- `rq03_rq04.csv`
- `rq05_rq06.csv`

Use nomes de colunas em `snake_case`, sem acentos e sem espacos.

Exemplo:

```csv
name_with_owner,created_at,repository_age_days,merged_pull_requests
```

## Padrao para validacao

Cada integrante deve validar uma amostra de 5 a 10 repositorios da sua parte.

A validacao deve conferir:

- se os campos obrigatorios vieram preenchidos;
- se valores numericos sao inteiros;
- se contagens nao sao negativas;
- se datas conseguem ser processadas;
- se casos com valor `0` sao tratados corretamente quando forem validos.

O script de validacao deve ficar em `code/src/validators/`.

Nome sugerido:

```text
rqXX_rqYY.py
```

## Padrao para scripts de analise

Os scripts que calculam metricas finais devem ficar em `code/src/analyzers/`.

Nome sugerido:

```text
rqXX_rqYY_metrics.py
```

O script deve:

- ler o CSV de `data/processed/`;
- calcular as metricas pedidas no enunciado;
- imprimir um resumo no terminal;
- gerar um Markdown em `reports/`.

Exemplo de execucao:

```powershell
python .\lab1\code\src\analyzers\rq01_rq02_metrics.py
```

## Padrao para responder as RQs

Cada resposta em Markdown deve ficar em `reports/`.

Nome sugerido:

```text
rqXX-rqYY.md
```

Cada RQ deve seguir esta estrutura:

```markdown
## RQXX - Pergunta

Resposta direta: Sim/Nao/Parcialmente.

Metrica usada: descrever a metrica do enunciado.

Resultados principais:

- Total de repositorios analisados: X
- Mediana: X
- Media: X
- Minimo: X
- Maximo: X

Discussao: interpretar os numeros em poucas frases, comparando com a hipotese quando existir.

Conclusao: frase final respondendo a pergunta.
```

Quando fizer sentido, incluir uma tabela pequena com os 5 repositorios mais relevantes para aquela RQ.

## RQs do Lab01

- RQ01: idade do repositorio a partir de `createdAt`.
- RQ02: total de pull requests aceitas, `pullRequests(states: MERGED).totalCount`.
- RQ03: total de releases.
- RQ04: tempo ate a ultima atualizacao.
- RQ05: linguagem primaria e comparacao com fonte externa escolhida.
- RQ06: razao entre issues fechadas e total de issues.
- RQ07: RQ02, RQ03 e RQ04 agrupadas por linguagem.

## Lab01S01

Escopo esperado:

- consulta GraphQL para os 100 repositorios mais populares;
- requisicao automatica via script proprio;
- coleta dos dados necessarios para as metricas;
- validacao rapida em amostra de 5 a 10 repositorios;
- GitHub Projects criado e em uso;
- colunas e limite de WIP documentados em `docs/kanban.md`.

## Checklist antes de commitar

- O script roda sem erro.
- A validacao da amostra foi executada.
- O CSV tem cabecalho claro.
- O Markdown da resposta foi gerado ou atualizado.
- O `.env` nao foi adicionado ao Git.
- O commit referencia a issue.

Comandos uteis:

```powershell
git status --short
python .\lab1\code\src\main.py
python .\lab1\code\src\analyzers\rq01_rq02_metrics.py
git add caminho/dos/arquivos
git commit -m "#NUMERO descricao objetiva"
```
