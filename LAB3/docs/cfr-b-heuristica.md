# Heurística de CFR(b)

## Unidade e censura

Para cada release primária, ordenada pela data de publicação, a release seguinte
é observada por até sete dias. A release atual é marcada como falha quando a
seguinte é publicada nesse intervalo e satisfaz a heurística corretiva.
Releases publicadas depois de `fim_da_janela - 7 dias` são mantidas como
`censored=true` e ficam fora do numerador e do denominador.

## Regra final

A release seguinte é corretiva se pelo menos uma evidência for verdadeira:

1. a transição é SemVer com mesmo `major` e `minor` e aumento de `patch`;
2. uma mensagem de commit no compare contém uma palavra inteira, sem distinção
   de maiúsculas, entre `fix`, `hotfix` e `revert`.

Assim, a regra é deliberadamente inclusiva: qualquer evidência sinaliza uma
correção, enquanto a ausência de evidência classifica a release anterior como
`nao_corretiva`.

O CFR(b) é `releases_falhas / releases_avaliadas`. A pipeline também grava os
casos censurados e as evidências acionadas em
`data/processed/metrics/cfr_b_predictions.csv`.

## Validação

`data/processed/gold_standard/gold_standard_consensus.csv` é a referência.
Linhas com `consensus_label=sem_release` permanecem na amostra para auditoria,
mas são excluídas da precisão, recall, F1 e matriz de confusão. A execução da
pipeline grava métricas, cobertura e matriz em
`reports/validation/cfr_b_validation.json`; previsões ausentes não são
convertidas silenciosamente em negativos.