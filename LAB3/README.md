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

## Sprint 1 — seleção de repositórios e funil

As issues `(LAB3S01 - 1)` e `(LAB3S01 - 2)` implementam a seleção inicial de candidatos e o funil da amostra de 100 repositórios.

### Preparar ambiente

```powershell
cd LAB3
python -m pip install -e .[dev]
```

### Executar com a API do GitHub

No PowerShell:

```powershell
cd LAB3
$env:GITHUB_TOKEN = "seu_token"
python -m lab03_dora.pipeline.select_repositories
```

Saídas geradas:

- `data/interim/selection/candidate_repositories.csv`: candidatos coletados e metadados básicos.
- `data/interim/selection/s01_repository_selection.csv`: candidatos classificados pelo funil.
- `reports/funnel/s01_selection_funnel.csv`: contagens por etapa do funil.

### Executar a partir de um CSV local

Para reprocessar o funil sem chamar a API:

```powershell
cd LAB3
python -m lab03_dora.pipeline.select_repositories --input-csv data/interim/selection/candidate_repositories.csv
```

### Testes

```powershell
cd LAB3
python -m pytest
```

Observação: nesta primeira etapa, quando as contagens de releases e workflow runs ainda não foram produzidas pelas issues seguintes, os 100 repositórios com GitHub Actions ficam marcados como `s01_base_sample`. Quando essas contagens existirem, o mesmo funil passa a classificar os repositórios como `eligible_s01` ou descartar por releases/runs insuficientes.
