# RQ07 — análise de sensibilidade

## Escopo

A análise foi executada sobre os 300 repositórios elegíveis da amostra final da Sprint 2.

## Variantes observadas

| Variante | Unidade de deploy | Lead time | CFR |
|---|---|---|---|
| C1 | release | por release | CFR(a) |
| C2 | release | por commit | CFR(b) |
| C3 | release | por release | CFR(b) |

Para cada repositório, a categoria geral é a mediana, arredondada para baixo, das quatro categorias métricas: frequência, lead time, CFR e recuperação. Casos sem alguma métrica necessária permanecem sem classificação e são excluídos somente do par correspondente.

## Resultados

Os valores completos estão em `pairwise_comparisons.csv` e `variant_summary.csv`. A matriz de transição e o percentual de mudança devem ser interpretados junto com `n_compared`, que informa quantos repositórios tinham classificação disponível nas duas variantes.

## Limitação

A coleta da variante baseada em tags não foi concluída para os 300 repositórios. O dataset S02 não contém contagem ou métricas derivadas de tags; portanto, não é possível afirmar uma comparação release versus tag. Nenhum valor foi simulado ou inferido.
