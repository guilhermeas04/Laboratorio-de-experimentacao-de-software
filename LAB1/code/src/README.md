# `src`

Codigo-fonte dos scripts do Lab01.

Arquivos principais previstos para a Lab01S01:

- `main.py`: ponto de entrada da coleta.
- `config.py`: leitura de configuracoes e variaveis de ambiente.
- `github_client.py`: cliente HTTP simples para GraphQL.
- `queries/top_repositories.graphql`: query dos repositorios populares.
- `collectors/repositories.py`: coleta e normalizacao inicial.
- `validators/rq01_rq02.py`: validacao da parte RQ01 + RQ02.
- `validators/rq03_rq04.py`: validacao da parte RQ03 + RQ04.
- `validators/rq05_rq06.py`: validacao da parte RQ05 + RQ06.
- `exporters/csv_exporter.py`: exportacao de dados tabulares.
- `exporters/project_snapshot.py`: estrutura para snapshots do GitHub Projects.
- `visualization/loader.py`: carregador unico do CSV consolidado.
- `visualization/style.py`: estilo comum Matplotlib/Seaborn (backend Agg).
- `visualization/figures.py`: pasta e convencao de nomes das figuras.
- `visualization/smoke_test.py`: grafico de teste do pipeline.
