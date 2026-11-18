# Dados intermediários

Arquivos derivados da coleta bruta, sem sobrescrever `data/raw/`.

`pilot_metrics.csv` é gerado dos JSONs validados em `data/raw/`. Cada linha
preserva a versão completa, o bloco pareado e o nome do JSON de origem.
`query_latency_ms` vem de `Execution Time` do PostgreSQL. As colunas de
throughput, CPU e memória ficam vazias até que sejam instrumentadas.
