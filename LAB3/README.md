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

## Sprint 1 — releases, tags e commits entre releases

A issue `(LAB3S01 - 3)` coleta releases, tags e os commits entre uma release e a anterior. Draft fica de fora da definição principal. Pré-release e tag são gravados para a análise de sensibilidade. A janela e o default branch vêm da configuração e do repositório.

Por padrão, o comando lê o CSV da seleção, coleta os 100 repositórios marcados como `s01_base_sample` e atualiza a coluna `releases_count` no mesmo arquivo:

```powershell
cd LAB3
$env:GITHUB_TOKEN = "seu_token"
python -m lab03_dora.collection.history
```

Para testar somente um repositório:

```powershell
python -m lab03_dora.collection.history --repo owner/nome --default-branch main
```

Saídas:

- `cache/api/<owner>__<repo>/`: respostas brutas de releases, tags e compare.
- `data/raw/github/releases/`, `tags/` e `commits/`: saídas intermediárias.
- `data/interim/release_history/`: casos ignorados ou com problema, sem interromper a coleta.
- `data/interim/release_history/release_changes.csv`: commits e datas por release, em formato consumível pelas métricas de lead time da issue #98.
- `data/interim/selection/s01_repository_selection.csv`: funil atualizado com a contagem de releases dos repositórios coletados.

## Sprint 1 — deployment frequency e lead time

A issue `(LAB3S01 - 5)` calcula as métricas sem chamar a API.

- RQ01, `lab03_dora.metrics.deployment_frequency`: releases publicadas na janela divididas pelo número de semanas. Para 2025-01-01 a 2025-12-31 isso é 365/7, cerca de 52,1.
- RQ02, `lab03_dora.metrics.lead_time`: mediana por release (data da release menos o commit mais antigo) e mediana por commit (data da release menos cada commit). A primeira release, release sem commit novo e data de commit posterior à publicação ficam de fora da mediana.

```powershell
cd LAB3
python -m pytest tests/unit/test_deployment_frequency.py tests/unit/test_lead_time.py
```

## Sprint 1 — workflow runs e confiabilidade

`lab03_dora.collection.workflow_runs` coleta execuções do GitHub Actions no
branch padrão, somente para `event=push`, particionando a janela em meses.
Cada consulta usa o intervalo `created=...` da API e grava as páginas em cache.
Os resultados podem ser coletados para a amostra inteira com
`collect_workflow_runs_for_repositories`.

```powershell
cd LAB3
$env:PYTHONPATH = "src"
python -m pytest
```

São aceitas apenas as conclusões `success`, `failure`, `timed_out` e
`startup_failure`; execuções canceladas, ignoradas ou em andamento ficam fora.
Meses com 1.000 ou mais resultados são sinalizados em `windows_at_limit` para
subdivisão adicional antes da análise final.
# Pipeline integrado da Sprint 1

O ponto de entrada executa a seleção, coleta de releases/tags/commits, workflow
runs, cache HTTP e as métricas iniciais em uma única execução:

```powershell
cd LAB3
python -m pip install -e ".[dev]"
$env:GITHUB_TOKEN = gh auth token       # ou defina um token pessoal equivalente
$env:PYTHONPATH = "src"                # necessário se não instalar o pacote
python -m lab03_dora.pipeline             # amostra S01 (até 100 repositórios)
python -m lab03_dora.pipeline --limit 3 --target-with-actions 3  # smoke real
```

`GITHUB_TOKEN` é obrigatório para consultar a API, nunca é gravado no cache ou
nas saídas. O cache permite retomar a coleta sem repetir requisições. As saídas
principais são `data/interim/selection/`, `data/cache/`/`cache/`,
`data/raw/workflow_runs/`, `reports/funnel/` e
`data/processed/metrics/s01_metrics.csv` (frequência, lead time, CFR e recuperação).

O workflow `.github/workflows/lab3-tests.yml` instala o projeto e executa
`pytest` automaticamente em todo push ou pull request que altere `LAB3/`.

## Versionamento dos dados

O cache da API e as respostas brutas ficam locais e são regeneráveis; eles não
devem ser adicionados ao Git. Os resultados tabulares consolidados e o manifesto
da execução podem ser versionados:

- `data/processed/metrics/s01_metrics.csv`
- `data/processed/metrics/s01_manifest.json`
- `reports/funnel/s01_selection_funnel.csv`
- `data/interim/selection/s01_repository_selection.csv`
