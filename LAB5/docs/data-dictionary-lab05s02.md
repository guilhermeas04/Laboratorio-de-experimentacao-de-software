# Dicionário de dados — LAB05S02

Este dicionário atualiza o contrato da coleta completa PostgreSQL. Os arquivos originais em `LAB5/data/raw/s02/<campanha>/` são preservados; o validador lê o manifesto e os registros sem modificá-los. O dataset derivado fica em `LAB5/data/processed/` e não contém imputações.

## Dataset validado

| Campo | Tipo | Unidade | Descrição |
|---|---|---|---|
| `campaign_id` | string | — | Identificador da campanha; deve coincidir com o manifesto. |
| `block` | inteiro positivo | bloco | Unidade de pareamento da comparação. |
| `position` | inteiro positivo | posição | Ordem da versão dentro do bloco. |
| `software_version` | enum | — | `15.20` ou `17.12`, conforme a configuração da campanha. |
| `scenario` | enum | — | `customer_total` ou `range_summary`. |
| `collected_at` | timestamp ISO-8601 | — | Início da rodada, com fuso horário. |
| `ended_at` | timestamp ISO-8601 | — | Término da rodada, posterior ou igual ao início. |
| `execution_id` | string | — | Identificador da tentativa do bloco. |
| `round_id` | string | — | Identificador estável da rodada; deve coincidir com o nome bruto sem extensão. |
| `source` | string | caminho relativo | Caminho rastreável até o arquivo JSON bruto. |
| `query_latency_ms` | número finito | ms | Mediana de cinco `Execution Time` do `EXPLAIN ANALYZE`; faixa válida não negativa. |
| `throughput_queries_per_second` | número finito | consultas/s | TPS do pgbench sem tempo de conexão inicial; faixa válida não negativa. |
| `cpu_percent` | número finito | % | Uso médio de CPU no cgroup; faixa válida de 0 a 100 por CPU configurada. |
| `memory_mb` | número finito | MB decimal | Média da memória do cgroup na janela amostrada; faixa válida não negativa. |
| `client_latency_ms` | número finito | ms | Latência média reportada pelo pgbench; faixa válida não negativa. |
| `resource_window_seconds` | número finito | s | Duração da janela usada para amostragem dos recursos; faixa válida não negativa. |

## Regras de validação

- O manifesto deve usar `lab05-s02-campaign-v1` e declarar `status=complete`.
- Cada rodada deve usar `lab05-s02-round-v1` e pertencer ao bloco, cenário e versão planejados.
- Deve haver consistência entre manifesto, campanha, tentativa, configuração, imagem, `round_id` e caminho bruto.
- Timestamps devem ser ISO-8601 com fuso horário; `ended_at` não pode preceder `collected_at`.
- A versão reportada pelo servidor deve corresponder à versão configurada.
- Métricas devem existir, ser numéricas e finitas, e respeitar suas unidades/faixas.
- A chave de duplicidade é `(block, scenario, software_version)`.
- Pares completos exigem as duas versões no mesmo bloco e cenário para cada métrica.
- Ausências permanecem vazias. Não há imputação silenciosa.
- Registros inválidos, duplicados e falhos são registrados no relatório de qualidade e excluídos do CSV.
