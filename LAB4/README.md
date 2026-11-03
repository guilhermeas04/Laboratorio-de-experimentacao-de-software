# LAB04 — Testes de hipótese por dentro

Laboratório de Experimentação de Software sobre simulação, comparação e
visualização de testes de hipótese.

## Objetivo

Comparar dois testes estatísticos que podem responder à mesma pergunta de
Engenharia de Software, medindo erro tipo I, poder estatístico e efeito de
violações de pressupostos por meio de dados simulados calibrados com uma
pequena amostra de dados reais.

## Par escolhido

O par será definido pelo grupo. As opções previstas no enunciado são:

| Par | Testes | Exemplo de cenário |
|---|---|---|
| P1 | t de Welch × Mann-Whitney | Tempo até o merge de PRs, com e sem bot de revisão |
| P2 | t pareado × Wilcoxon pareado | Tempo de build antes e depois de ativar cache |
| P3 | ANOVA × Kruskal-Wallis | Tempo de revisão por tamanho de PR |
| P4 | Z para proporção × binomial exato | Taxa de builds com falha diante de uma meta |
| P5 | Pearson × Spearman | LOC de módulo × número de defeitos |

O cenário, a escolha final e a justificativa estão em
[`docs/proposta-lab04.md`](docs/proposta-lab04.md).

## Estrutura

```text
LAB4/
├── config/                 # semente, alpha, tamanhos de efeito e parâmetros
├── data/
│   ├── raw/                # dados reais coletados, sem alterações
│   ├── interim/            # dados limpos e parâmetros estimados
│   └── processed/          # resultados das simulações e tabelas finais
├── docs/                   # proposta, protocolo e dicionário de dados
├── notebooks/              # exploração e análises auxiliares
├── reports/
│   ├── figures/            # G1, G2, G3 e G4
│   └── tables/             # estatísticas, p-valores e tamanhos de efeito
├── dashboard/              # aplicação ou página final do laboratório
├── src/lab04_hypothesis/   # coleta, testes, simulação, gráficos e pipeline
├── tests/                  # testes unitários e de integração
└── requirements.txt
```

## Requisitos da análise

- Usar semente fixa para garantir reprodutibilidade.
- Coletar cerca de 30 observações por grupo comparado.
- Executar 10.000 repetições para Q1 e Q2.
- Medir erro tipo I, poder e pelo menos uma violação de pressuposto.
- Avaliar no mínimo cinco tamanhos de efeito, começando em zero.
- Gerar G1, G2, G3 e G4 com títulos, eixos, unidades e legenda.
- Reportar estatística, p-valor, tamanho do efeito e conclusão para os dados reais.

## Execução prevista

Na raiz do repositório:

```powershell
python -m pip install -r .\LAB4\requirements.txt
$env:PYTHONPATH = "LAB4/src"
python -m lab04_hypothesis.pipeline
```

O comando gera a amostra simulada de exemplo, aplica Welch e Mann-Whitney,
grava as tabelas em `reports/tables/`, as figuras G1/G2 em `reports/figures/`
e atualiza `dashboard/index.html`. Use `--null-replications` para controlar
quantas repeticoes alimentam o G2 (padrao: ate 2000).

### LAB04S01 — coleta dos dados reais

Para reexecutar a coleta dos 30 PRs por grupo:

```powershell
$env:PYTHONPATH = "LAB4/src"
python LAB4/src/lab04_hypothesis/collect_real_data.py
```

A coleta não sobrescreve dados brutos existentes. Para reprocessar explicitamente e substituir as saídas, use `--force`.

O comando usa `GITHUB_TOKEN` quando aceito pela API e faz fallback para a API
pública em caso de token rejeitado. Os dados brutos e o metadata são gravados
em `LAB4/data/raw/`. Os testes do coletor rodam com:

```powershell
python -m pytest LAB4/tests
```

## Dashboard

O dashboard final deverá conter, nesta ordem:

1. Cenário;
2. Os dados — G1;
3. Como os testes funcionam — G2;
4. Erro tipo I — G3;
5. Poder — G4;
6. Dados reais;
7. Conclusão e recomendação.

Cada gráfico deve ter um texto curto explicando o resultado e sua interpretação.

