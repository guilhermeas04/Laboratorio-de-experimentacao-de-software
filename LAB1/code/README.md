# Codigo do Lab01

## Pastas

- `src/queries/`: consultas GraphQL escritas pelo grupo.
- `src/collectors/`: scripts responsaveis por chamar a API do GitHub.
- `src/validators/`: validacoes rapidas por RQ.
- `src/exporters/`: exportacao de resultados e snapshots.
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
