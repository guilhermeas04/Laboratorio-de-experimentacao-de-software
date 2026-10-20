# RQ01 e RQ02

Repositórios considerados: **300** (alvo: 300).
Valores ausentes não foram convertidos em zero e ficam fora das estatísticas da métrica.

| Métrica | N válido | Ausentes | Mediana | Q1 | Q3 | IQR |
|---|---:|---:|---:|---:|---:|---:|
| deployment_frequency_per_week | 300 | 0 | 0.2493 | 0.1342 | 0.5370 | 0.4027 |
| lead_time_by_release_days | 300 | 0 | 11.6280 | 2.2709 | 35.1451 | 32.8741 |
| lead_time_by_commit_days | 300 | 0 | 10.7128 | 2.2464 | 29.6179 | 27.3715 |

## Classificação

Cortes aplicados: deployment frequency `< 1/mês`, `1/mês a < 1/semana`, `1 a < 7/semana`, `>= 7/semana`; lead time `< 1`, `1 a < 7`, `7 a < 30`, `>= 30` dias.
Repositórios sem valor recebem `ausente` e não são classificados como Low.
