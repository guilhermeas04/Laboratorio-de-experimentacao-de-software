# Critérios de agregação — análise descritiva LAB05S02

Dataset validado: `LAB5/data/processed/lab05s02-20261121-01_validated.csv`

A análise usa apenas rodadas presentes no CSV validado. Valores ausentes
permanecem NaN, entram em `n_missing` e nunca são imputados como zero.
O identificador `block` é preservado nas tabelas de pares e de rastreabilidade,
com o caminho bruto em `source`.
As contagens descrevem as rodadas presentes no CSV. Rodadas excluídas
e pares totalmente ausentes constam do relatório de qualidade da coleta.
Cada painel de distribuição usa escala vertical própria.

| Métrica | Unidade | Escala | Critério de agregação |
|---|---|---|---|
| `query_latency_ms` | ms | ratio | Mediana de cinco Execution Time do EXPLAIN ANALYZE por rodada; na análise descritiva, cada rodada validada é uma observação. |
| `throughput_queries_per_second` | consultas/s | ratio | TPS do pgbench sem tempo de conexão inicial; cada rodada validada contribui com um valor. |
| `cpu_percent` | % | ratio | Média do uso de CPU no cgroup na janela amostrada; sem imputação de ausentes. |
| `memory_mb` | MB | ratio | Média da memória do cgroup na janela amostrada; sem imputação de ausentes. |
| `client_latency_ms` | ms | ratio | Latência média reportada pelo pgbench por rodada. |
| `resource_window_seconds` | s | ratio | Duração da janela usada para amostrar CPU/memória. |
