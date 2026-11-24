# Inferência pareada — LAB05S02

Contraste pré-especificado no desenho da Sprint 2:

- versões: `15.20` (A) versus `17.12` (B);
- cenário/métrica primários: `customer_total` / `query_latency_ms`;
- unidade de análise: bloco pareado;
- H0: diferença média pareada igual a zero; alternativa bilateral; alfa = 0,05;
- teste confirmatório: t pareado, quando os pressupostos forem sustentáveis;
- demais métricas/cenários: exploratórios, com ajuste de Holm.

## Resultado primário

- pares completos: **24**;
- diferença média A−B: **0.02008333333333333**;
- IC 95%: **[0.007754791032821713, 0.03241187563384495]**;
- p-valor: **0.002644580698448968**;
- status da inferência: **assumption_warning**;
- Cohen d_z: **0.6878710965104499**;
- relevância prática (≥ 10%): **threshold_not_met** (mudança relativa observada = 4.8983739837398375%).

## Métricas secundárias

Foram avaliados 9 contrastes exploratórios. Os p-valores ajustados por Holm estão em `reports/tables/s02_paired_secondary_inference.csv`.

## Leitura

O teste t e seu intervalo são apresentados com ressalva quando Shapiro–Wilk aponta desvio de normalidade. Nesse caso, a decisão confirmatória fica indeterminada e Wilcoxon é apresentado como sensibilidade exploratória. A avaliação de normalidade não verifica independência entre os blocos.

A relevância prática compara a estimativa pontual ao limiar definido antes da coleta. Consulte os [diagnósticos de validade](validade-lab05s02.md) para a estabilidade por ordem e bloco.
