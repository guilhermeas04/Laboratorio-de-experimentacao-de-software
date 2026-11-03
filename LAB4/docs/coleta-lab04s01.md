# LAB04S01: coleta de dados reais

## Cenário escolhido

Foi escolhido o par P1: tempo até o merge de pull requests de autoria de bot
versus autoria humana. Cada observação é um pull request público mesclado.

- H0: os tempos de merge dos dois grupos não diferem.
- H1: os tempos de merge dos dois grupos diferem.
- Unidade: horas entre `created_at` e `merged_at`.
- O teste planejado para a próxima sprint é bicaudal.

## Fonte e procedimento

Os dados vêm da API REST pública do GitHub, no endpoint
`GET /repos/{owner}/{repo}/pulls` com `state=closed`, usando os repositórios do
dataset final do LAB3 como universo de candidatos. A coleta é executada por
`LAB4/src/lab04_hypothesis/collect_real_data.py` e requer `GITHUB_TOKEN`.
O timestamp da coleta, a fonte, os critérios e as limitações ficam registrados
em `LAB4/data/raw/collection_metadata.json`.

## Grupos e critérios

O grupo `bot` é definido quando `user.type == Bot` ou o login termina em
`[bot]`. Os demais autores formam o grupo `human`. Entram somente PRs fechados
com `merged_at`, `created_at` válido e duração não negativa. PRs não mesclados,
sem timestamps, com duração negativa e observações após as primeiras 30 de cada
grupo são excluídos.

Os dados brutos não são transformados e ficam em
`LAB4/data/raw/pr_merge_time.csv`. A unidade e o dicionário das colunas estão
descritos no próprio metadata da coleta.

## Limitações

Esta é uma amostra de conveniência, dependente dos repositórios públicos e das
últimas páginas retornadas pela API. `user.type` é um proxy operacional para
automação e pode classificar incorretamente integrações que usam contas humanas.
Os dados não representam todos os projetos GitHub nem permitem inferir
causalidade entre autoria automatizada e tempo de merge.