# LAB02 - Dashboard

Dashboard reproduzivel baseado exclusivamente nos 18 trials oficiais do contrabalanceamento.

- Trials: 18
- Participantes: 3
- Trials censurados: 0

As figuras mostram cada trial como ponto, com mediana e IQR por tratamento. Pontos de trials censurados, quando existirem, sao marcados com X vermelho no grafico de tempo.

## Artefatos

- `figures/dashboard-rq1-time.png`: RQ1, tempo por tratamento.
- `figures/dashboard-rq2-outcomes.png`: RQ2, taxa de sucesso e testes falhando.
- `figures/dashboard-rq3-static-metrics.png`: RQ3, metricas estaticas.
- `dashboard-trials.csv`: tabela unificada por trial.
- `dashboard-summary.csv`: mediana, quartis e IQR por tratamento e metrica.

## Resumo

| Tratamento | Metrica | n | Q1 | Mediana | Q3 | IQR | Min | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Com IA | Tempo (s) | 9 | 4.359 | 18.073 | 30.063 | 25.704 | 0.135 | 308.704 |
| Com IA | Taxa de sucesso (%) | 9 | 100.0 | 100.0 | 100.0 | 0.0 | 100.0 | 100.0 |
| Com IA | Testes falhando | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Com IA | LOC | 9 | 23.0 | 32.0 | 34.0 | 11.0 | 12.0 | 40.0 |
| Com IA | CC media | 9 | 6.0 | 13.0 | 19.0 | 13.0 | 5.0 | 25.0 |
| Com IA | CC maxima | 9 | 8.0 | 13.0 | 19.0 | 11.0 | 6.0 | 25.0 |
| Com IA | Duplicacao (%) | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Com IA | Indice de manutenibilidade | 9 | 49.761 | 50.727 | 53.807 | 4.046 | 43.633 | 63.438 |
| Manual | Tempo (s) | 9 | 0.283 | 24.712 | 322.484 | 322.201 | 0.143 | 487.28 |
| Manual | Taxa de sucesso (%) | 9 | 100.0 | 100.0 | 100.0 | 0.0 | 100.0 | 100.0 |
| Manual | Testes falhando | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Manual | LOC | 9 | 19.0 | 25.0 | 43.0 | 24.0 | 13.0 | 47.0 |
| Manual | CC media | 9 | 11.0 | 14.0 | 22.0 | 11.0 | 6.0 | 27.0 |
| Manual | CC maxima | 9 | 11.0 | 14.0 | 22.0 | 11.0 | 6.0 | 27.0 |
| Manual | Duplicacao (%) | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Manual | Indice de manutenibilidade | 9 | 44.439 | 50.874 | 56.138 | 11.699 | 42.33 | 63.127 |

## Reproducao

A partir de `LAB2/code`, execute `python -m lab02.dashboard` (ou `lab02-dashboard` apos instalar o pacote).
