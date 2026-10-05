# LAB3 — Mineração de Métricas DORA

Estrutura inicial para o laboratório de mineração das métricas DORA em repositórios open-source com GitHub Actions.

## Organização

- `config/`: arquivos de configuração do pipeline, como janela de observação, tamanho da amostra e parâmetros de coleta.
- `src/lab03_dora/`: código-fonte do pipeline.
  - `api/`: cliente REST/GraphQL próprio para GitHub, paginação, rate limit e backoff.
  - `collection/`: seleção de repositórios e coleta de releases, commits, tags e workflow runs.
  - `metrics/`: cálculo das métricas DORA, classificação e funções reutilizáveis.
  - `analysis/`: análises estatísticas das RQs.
  - `validation/`: validação manual, amostra-ouro, kappa, precisão, recall e F1.
  - `pipeline/`: orquestração para execução com comando único.
  - `utils/`: utilitários compartilhados.
- `tests/`: testes unitários e de integração, com fixtures pequenas e controladas.
- `data/`: dados do estudo.
  - `raw/`: respostas brutas da API, normalmente regeneráveis e não versionadas.
  - `interim/`: dados intermediários, funil de seleção e planilhas de validação manual.
  - `processed/`: datasets finais, métricas calculadas e amostra-ouro consolidada.
- `cache/`: cache local de API/SQLite para retomada da coleta.
- `notebooks/`: explorações e análises por grupos de RQs.
- `reports/`: tabelas, figuras e funil de seleção usados no artigo.
- `docs/`: metodologia, artigo, dicionário de dados e documentação de replicação.
- `scripts/`: comandos auxiliares de desenvolvimento.

## Requisito central

O pipeline final deve ser reprodutível por outro grupo a partir do README, com um único comando, lendo o token do GitHub por variável de ambiente (`GITHUB_TOKEN`) e sem usar bibliotecas prontas de acesso à API do GitHub.
