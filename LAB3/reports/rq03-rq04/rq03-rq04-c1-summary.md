# RQ03, RQ04 e DORA C1

Repositórios considerados: **300** (alvo: 300).
Ausentes ficam fora da mediana/IQR e não são convertidos em zero.

| Métrica | N válido | Ausentes | Mediana | Q1 | Q3 | IQR |
|---|---:|---:|---:|---:|---:|---:|
| cfr_a | 300 | 0 | 0.0503 | 0.0144 | 0.1172 | 0.1028 |
| cfr_b | 299 | 1 | 0.2903 | 0.1000 | 0.4667 | 0.3667 |
| recovery_median_hours | 261 | 39 | 0.3953 | 0.0778 | 6.0644 | 5.9867 |
| recovery_censored_count | 300 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Definições

- CFR(a): falhas de workflow / (falhas + sucessos) válidos.
- CFR(b): release seguida por corretiva em até 7 dias; releases dos últimos 7 dias são censuradas.
- Recuperação: mediana em horas dos episódios encerrados; episódios sem sucesso até o fim da janela são censurados.
- C1: deployment por release, lead time por release, CFR(a) e recuperação; a nota geral é a mediana inteira inferior das quatro notas.

Episódios de recuperação censurados: 24 em 24 repositórios.
