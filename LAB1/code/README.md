# Codigo do Lab01

## Pastas

- `src/queries/`: consultas GraphQL escritas pelo grupo.
- `src/collectors/`: scripts responsaveis por chamar a API do GitHub.
- `src/validators/`: validacoes rapidas por RQ.
- `src/exporters/`: exportacao de resultados e snapshots.
- `src/visualization/`: carregador do CSV, estilo comum e geracao de figuras.
- `tests/`: testes automatizados ou amostras de validacao.

## Variaveis de ambiente

Crie um arquivo `.env` local com base em `.env.example`.

```env
GITHUB_TOKEN=seu_token_aqui
GITHUB_GRAPHQL_URL=https://api.github.com/graphql
GITHUB_TOP_REPOSITORIES_LIMIT=1000
```

Nao versionar tokens reais.

## Execucao (Lab01S02)

Na raiz do repositorio:

```bash
cd LAB1/code
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

A coleta pagina a consulta GraphQL (`pageInfo`, `endCursor`, `after`), remove
duplicatas por `name_with_owner` e exporta exatamente 1000 repositorios em
`LAB1/data/processed/top_repositories.csv`.

Ao final, o script valida:

- quantidade de linhas (1000);
- cabecalho com todos os campos das RQ01 a RQ07;
- ausencia de duplicatas;
- preenchimento basico dos campos obrigatorios.

Validacao das RQ03 e RQ04 nos 1000 registros:

```bash
python src/analyzers/rq03_rq04_metrics.py
```

## Execucao (Lab01S03) - pipeline de visualizacao

O pacote `src/visualization/` carrega `LAB1/data/processed/top_repositories.csv`,
valida quantidade/tipos/colunas e aplica um estilo comum (Matplotlib/Seaborn com
backend `Agg`, sem interface grafica).

Figuras ficam em `LAB1/reports/figures/` com a convencao `rqXX_<slug>.png`
(ex.: `rq03_releases.png`).

Grafico de teste do pipeline:

```bash
cd LAB1/code
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/visualization/smoke_test.py
```

Visualizacoes das RQ01 e RQ02:

```bash
python src/analyzers/rq01_rq02_plots.py
```

O comando gera `rq01_idade.png` e `rq02_pull_requests.png` em
`LAB1/reports/figures/` e acrescenta a interpretacao objetiva ao relatorio
`LAB1/reports/rq01-rq02.md`.

Visualizacoes das RQ03 e RQ04:

```bash
python src/analyzers/rq03_rq04_plots.py
```

As figuras sao salvas em `LAB1/reports/figures/rq03_releases.png` e
`LAB1/reports/figures/rq04_atualizacao.png`.

Visualizacoes das RQ05, RQ06 e RQ07:

```bash
python src/analyzers/rq05_rq07_plots.py
```

O comando gera `rq05_linguagens.png`, `rq06_issues.png` e
`rq07_linguagem_metricas.png` em `LAB1/reports/figures/`, além do relatório
objetivo `LAB1/reports/rq05-rq06-rq07-visualizacoes.md`.

Snapshot do GitHub Projects:

```bash
set GITHUB_PROJECT_OWNER=guilhermeas04
set GITHUB_PROJECT_NUMBER=3
python src/exporters/project_snapshot.py
```

O snapshot e salvo com timestamp em `LAB1/data/snapshots/` e registra os itens,
issues, responsaveis e status atual do Project.
