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

## Dashboard

Esta entrega finaliza os artefatos visuais da LAB02S03, relacionada a #86.

O dashboard consolida diretamente o desenho oficial, os registros em `data/raw/`
e as metricas em `data/processed/`. A partir de `LAB2/code`, um unico comando
recria as tabelas e as figuras:

```powershell
python -m lab02.dashboard
```

O comando usa somente os 18 trials de `data/design/counterbalancing.csv`, ignora
arquivos extras e grava em `reports/`:

- `dashboard-trials.csv`: tabela unificada de RQ1/RQ2/RQ3 por trial;
- `dashboard-summary.csv`: n, quartis, mediana e IQR por tratamento;
- `dashboard-summary.md`: resumo citavel e inventario dos artefatos;
- `figures/dashboard-rq1-time.png`: tempo por tratamento;
- `figures/dashboard-rq2-outcomes.png`: taxa de sucesso e testes falhando;
- `figures/dashboard-rq3-static-metrics.png`: metricas estaticas.

Cada ponto representa um trial e a caixa resume mediana/IQR. Trials censurados
sao mantidos no tempo registrado e marcados com X vermelho na figura da RQ1.

Depois da geracao, a validacao automatica confere tabela 18/18, IDs oficiais,
cabecalho PNG, tamanho minimo de 10 KB e dimensoes minimas de 640 x 400 px:

```powershell
python -m lab02.validate_dashboard
```

O proprio `python -m lab02.dashboard` executa essa validacao ao final. Falhas
de existencia, formato, dimensao ou tabela interrompem o comando com codigo
diferente de zero.
