# Relatorios e visualizacoes

Resultados, tabelas, figuras e o relatorio final sao gerados neste diretorio.
Dados ficticios de `LAB2/data/examples/` nao podem ser usados nas analises.

## RQ1/RQ2

Gere os artefatos estatisticos de tempo e defeitos com:

```powershell
cd LAB2/code
lab02-rq12
```

Arquivos esperados:

- `rq12-trials.csv`: tabela consolidada dos 18 trials oficiais.
- `rq12-statistics.json`: estatisticas descritivas e Wilcoxon pareado.
- `rq12-summary.md`: resumo em Markdown para o relatorio final.

## RQ3

Gere a consolidacao das metricas estaticas e o resumo da RQ3 com:

```powershell
cd LAB2/code
lab02-rq3
lab02-rq3 --check-completeness
```

Arquivos esperados:

- `rq3-trials.csv`: LOC, complexidade, duplicacao e MI por trial oficial.
- `rq3-statistics.json`: descritivas, Wilcoxon bicaudal, Holm e completude.
- `rq3-summary.md`: tabelas finais e interpretacao da RQ3.
