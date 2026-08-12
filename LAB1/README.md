# LAB1 — Repositórios populares e setup do Kanban

O Laboratório 01 estuda características de projetos open source populares por
meio da API GraphQL do GitHub. A coleta inicial da sprint Lab01S01 considera os
100 repositórios com mais estrelas e reúne os dados necessários para responder
às questões de pesquisa do laboratório.


## Questões de pesquisa e métricas

| RQ | Questão investigada | Campo ou métrica coletada |
|---|---|---|
| RQ01 | Sistemas populares são maduros/antigos? | Idade calculada a partir de `createdAt` |
| RQ02 | Sistemas populares recebem muita contribuição externa? | `pullRequests(states: MERGED).totalCount` |
| RQ03 | Sistemas populares lançam releases com frequência? | `releases.totalCount` |
| RQ04 | Sistemas populares são atualizados com frequência? | Dias desde `updatedAt` |
| RQ05 | São escritos nas linguagens mais populares? | `primaryLanguage.name` |
| RQ06 | Possuem alto percentual de issues fechadas? | Issues fechadas divididas pelo total de issues |
| RQ07 | A linguagem influencia contribuição, releases e atualização? | Métricas das RQ02, RQ03 e RQ04 agrupadas por linguagem |

Para a RQ05, a referência escolhida para linguagens populares é o
[GitHub Octoverse 2024](https://github.blog/news-insights/octoverse/octoverse-2024/).

## Lab01S01

A primeira sprint foi dividida entre os integrantes da seguinte forma:

| Responsável | Atividade | Issue |
|---|---|---|
| Guilherme de Almeida Santos | Configuração do repositório e GitHub Projects | [#10](https://github.com/guilhermeas04/Laboratorio-de-experimentacao-de-software/issues/10) |
| Guilherme de Almeida Santos | RQ01 e RQ02 | [#11](https://github.com/guilhermeas04/Laboratorio-de-experimentacao-de-software/issues/11) |
| Pedro Rodrigues Duarte | RQ03 e RQ04 | [#12](https://github.com/guilhermeas04/Laboratorio-de-experimentacao-de-software/issues/12) |
| Amanda Bicalho Silva | RQ05 e RQ06 | [#13](https://github.com/guilhermeas04/Laboratorio-de-experimentacao-de-software/issues/13) |
| Pedro Rodrigues Duarte | Integração da consulta GraphQL | [#14](https://github.com/guilhermeas04/Laboratorio-de-experimentacao-de-software/issues/14) |
| Amanda Bicalho Silva | Automatização da coleta | [#15](https://github.com/guilhermeas04/Laboratorio-de-experimentacao-de-software/issues/15) |

A consulta integrada coleta 100 repositórios automaticamente em lotes de 10,
evitando falhas de gateway da API. Antes da exportação, o programa valida uma
amostra de 10 repositórios para conferir os campos e métricas das RQ01 a RQ06.

## GitHub Projects e Kanban

- Project: [Kanban](https://github.com/users/guilhermeas04/projects/3)
- Repositório vinculado: [Laboratorio-de-experimentacao-de-software](https://github.com/guilhermeas04/Laboratorio-de-experimentacao-de-software)
- Cartões: Issues reais do repositório, sempre atribuídas a um responsável
- Fluxo: `Backlog → To do → Doing → Review → Done`

### Política de WIP

A coluna **Doing** possui limite de **3 Issues simultâneas**.

O limite corresponde a uma atividade em andamento por integrante. Essa política
permite que os três membros trabalhem individualmente nas partes distribuídas da
sprint, evitando que uma mesma pessoa acumule várias tarefas abertas. Ao atingir
o limite, uma Issue deve avançar para `Review` ou `Done` antes que outra seja
movida para `Doing`.

As Issues devem refletir o andamento real do trabalho, possuir Assignee e estar
vinculadas ao Project. Cada commit deve mencionar a Issue correspondente, por
exemplo:

```text
#15 corrige coleta automatica e executa validacoes
```

## Estrutura

```text
LAB1/
├── code/
│   ├── .env.example
│   └── src/
│       ├── analyzers/    # cálculo e interpretação das métricas
│       ├── collectors/   # coleta e normalização dos dados
│       ├── exporters/    # exportação de CSV e snapshots
│       ├── queries/      # consultas GraphQL
│       ├── validators/   # validação de amostras
│       ├── config.py
│       ├── github_client.py
│       └── main.py
├── data/                 # dados brutos, processados e snapshots
├── docs/                 # documentação complementar
└── reports/              # resultados e relatório final
```

## Configuração

Crie o arquivo `LAB1/code/.env` com base em `LAB1/code/.env.example`:

```env
GITHUB_TOKEN=seu_token_do_github
GITHUB_GRAPHQL_URL=https://api.github.com/graphql
GITHUB_TOP_REPOSITORIES_LIMIT=100
```

O token precisa permitir consultas à API do GitHub. O arquivo `.env` é local,
está protegido pelo `.gitignore` e não deve ser commitado.

Instale as dependências:

```powershell
python -m pip install -r .\LAB1\code\requirements.txt
```

## Execução

Na raiz do repositório, execute:

```powershell
python .\LAB1\code\src\main.py
```

O programa:

1. carrega as configurações do `.env`;
2. consulta os 100 repositórios mais populares;
3. calcula as métricas derivadas;
4. valida 10 registros para as RQ01 a RQ06;
5. gera `LAB1/data/processed/top_repositories.csv`.

A execução pode levar aproximadamente de 30 a 90 segundos, pois são realizadas
dez requisições GraphQL para reduzir a carga de cada resposta e evitar erros
`502 Bad Gateway`.

## Dados gerados

O CSV contém as seguintes colunas:

- `name_with_owner` e `stargazer_count`;
- `created_at` e `repository_age_days`;
- `merged_pull_requests`;
- `updated_at` e `days_since_last_update`;
- `releases_count`;
- `primary_language`;
- `total_issues`, `closed_issues` e `closed_issues_ratio`.

Os arquivos gerados em `data/processed`, os snapshots e o `.env` não são
versionados automaticamente.

## Relatórios das questões de pesquisa

- [RQ01 e RQ02](reports/rq01-rq02.md)
- [RQ03 e RQ04](reports/rq03-rq04.md)
- [RQ05 e RQ06](reports/rq05-rq06.md)
- [RQ07](reports/rq07.md)
