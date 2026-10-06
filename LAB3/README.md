# LAB3 — Métricas DORA e integração contínua

Este diretório reúne a coleta de dados do GitHub Actions para as métricas DORA.
A issue #99 implementa a coleta de workflow runs do branch padrão, somente para
eventos `push`.

## Estrutura

```text
LAB3/
├── code/
│   ├── src/lab03_dora/collection/  # coletor e normalização
│   └── tests/                      # testes e fixtures
├── data/
│   ├── raw/                       # respostas brutas cacheadas
│   └── interim/                    # dados intermediários
├── docs/                           # protocolo e decisões
└── reports/                        # resultados consolidados
```

## Executar

```powershell
cd LAB3/code
python -m pip install -e .
python -m pytest
```

A função `collect_workflow_runs` recebe o repositório, o branch padrão e uma
janela UTC configurável. Ela divide a janela em meses, envia `event=push` e
`branch=<default branch>`, salva cada página em `data/raw/workflow_runs/` e
retorna apenas runs concluídos com conclusão `success`, `failure`, `timed_out`
ou `startup_failure`. Runs cancelados, ignorados, neutros, pendentes ou com
outras conclusões são descartados.

O resultado também informa `windows_at_limit`: os meses em que a API reportou
`total_count >= 1000`, para investigação e eventual subdivisão adicional.

## Resiliência e métricas

`lab03_dora.api.GitHubApiClient` mantém respostas em cache por rota e
parâmetros, espera o horário informado por `X-RateLimit-Reset` quando o limite
é atingido e repete erros 5xx com backoff exponencial. O token é usado somente
no cabeçalho da requisição e nunca é salvo no cache.

Em `lab03_dora.metrics`, `calculate_cfr` calcula a proporção de falhas entre
execuções válidas. `calculate_recovery` agrupa falhas consecutivas até o
primeiro sucesso posterior e registra como censurado o episódio que termina
sem recuperação antes do fim da observação.
