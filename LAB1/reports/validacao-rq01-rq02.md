# Validação das RQ01 e RQ02 — Lab01S02

Base validada: **1000 repositórios**.

## Objetivo

Verificar a consistência dos campos usados para calcular a idade dos repositórios (RQ01) e o total de Pull Requests aceitas (RQ02), considerando todos os 1.000 registros da coleta paginada.

## Integridade da base

- Registros esperados: 1.000
- Registros analisados: 1000
- Repositórios únicos: 1000
- Repositórios duplicados: 0
- `name_with_owner` ausente: 0
- `created_at` ausente: 0
- `repository_age_days` ausente: 0
- `merged_pull_requests` ausente: 0
- Datas inválidas: 0
- Idades negativas ou com tipo inválido: 0
- Contagens de PRs negativas ou com tipo inválido: 0

Os validadores interrompem a execução caso encontrem quantidade incorreta de registros, duplicidade, campo obrigatório ausente, data inválida, tipo incorreto ou valor negativo.

## Distribuições

| Métrica | Mínimo | Q1 | Mediana | Média | Q3 | Máximo | Outliers IQR |
|---|---:|---:|---:|---:|---:|---:|---:|
| Idade do repositório (dias) | 5 | 1282.50 | 2829 | 2798.90 | 4147.75 | 6703 | 0 |
| Pull Requests aceitas | 0 | 175 | 768 | 4233.82 | 3413.50 | 103313 | 124 |

## Critério de outlier

Foram considerados possíveis outliers os valores abaixo de `Q1 - 1,5 × IQR` ou acima de `Q3 + 1,5 × IQR`. Eles foram mantidos na base por representarem projetos reais e relevantes, não erros de coleta.

### Possíveis outliers de idade

Total: **0**.

Nenhum outlier identificado pelo método IQR.

### Possíveis outliers de Pull Requests aceitas

Total: **124**.

- `firstcontributions/first-contributions`: 103313
- `llvm/llvm-project`: 96964
- `elastic/elasticsearch`: 95472
- `getsentry/sentry`: 91156
- `home-assistant/core`: 90088
- `rust-lang/rust`: 73573
- `grafana/grafana`: 69387
- `ClickHouse/ClickHouse`: 69089
- `kubernetes/kubernetes`: 65650
- `python/cpython`: 62642
- … e mais 114 registros

## Recortes adicionais de RQ02

- Repositórios com 0 PRs aceitas: 20
- Repositórios com pelo menos 100 PRs aceitas: 819
- Repositórios com pelo menos 1.000 PRs aceitas: 452

## Resultado

Os **1000 repositórios** passaram pelas verificações estruturais de RQ01 e RQ02. Não foram encontrados registros duplicados, campos obrigatórios ausentes ou valores inválidos. Os outliers identificados foram documentados e preservados para as análises, pois refletem a assimetria esperada em métricas de repositórios populares.
