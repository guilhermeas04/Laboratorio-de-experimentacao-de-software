# Metodologia

Esta seção descreve a coleta versionada da Sprint 1 e a consolidação da Sprint 2. O dataset está em `data/processed/datasets/s02_metrics.csv`. O significado de cada coluna está em `data/processed/datasets/s02_data_dictionary.csv`.

## Amostra e filtros

A busca usa a API REST do GitHub, por faixas de estrelas, em repositórios não arquivados. O cliente é o módulo `lab03_dora.api.github`, sem biblioteca pronta de acesso à API. O token fica na variável `GITHUB_TOKEN`.

Entram na amostra final os repositórios com GitHub Actions, pelo menos 5 releases primárias e pelo menos 50 workflow runs válidos dentro da janela. Release primária é publicação com `draft = false` e `prerelease = false`, no default branch. Workflow run válido é execução de `push` nesse branch.

A tabela versionada processou 100 repositórios. Depois dos dois cortes numéricos restam 5 elegíveis. O alvo da issue #109 é 300 elegíveis. Esse alvo não fecha com a coleta que está no Git: as respostas brutas ficam fora do repositório e a nova coleta depende do token. O comando de reprodução está no README. O funil contado a partir da seleção atual está em `reports/funnel/s02_selection_funnel.csv`. Repositório repetido fica de fora; a consolidação guarda a primeira ocorrência e registra a contagem de duplicatas no manifesto.

## Janela e endpoints

A janela é 2025-01-01 a 2025-12-31, inclusive, em `config/lab3s02.json`. Semanas da janela: 365/7.

| Dado | Endpoint |
|---|---|
| Candidatos | `GET /search/repositories` |
| Releases | `GET /repos/{owner}/{repo}/releases` |
| Tags | `GET /repos/{owner}/{repo}/tags` |
| Commits entre releases | `GET /repos/{owner}/{repo}/compare/{base}...{head}` |
| Workflow runs | `GET /repos/{owner}/{repo}/actions/runs` |

## Variáveis

Frequência de deploy: releases primárias da janela divididas por 365/7.

Lead time, variante por release: data da release menos o commit mais antigo do compare com a release anterior. O valor do repositório é a mediana. A primeira release e a release sem commit novo ficam de fora. O campo vazio não vira zero.

Lead time, variante por commit: data da release menos cada commit incluído. O valor do repositório é a mediana de todos esses commits.

CFR(a): falhas de CI divididas por falhas mais sucessos. Execução cancelada não entra.

CFR(b): heurística validada na issue #108. Uma release falha se, em até 7 dias, a seguinte é corretiva. A seguinte é corretiva quando a transição SemVer sobe só o patch ou quando um commit do compare contém `fix`, `hotfix` ou `revert`. Releases dos últimos 7 dias da janela são censuradas e saem do denominador. A regra está em `docs/cfr-b-heuristica.md`.

Tempo de recuperação: mediana, em horas, do intervalo entre a primeira falha de um workflow e o sucesso seguinte. Episódio sem sucesso até o fim da janela fica censurado.

## Validação manual

Três avaliadores rotularam os mesmos 60 repositórios, sem copiar o rótulo alheio. O consenso e o kappa estão em `data/processed/gold_standard/`. No lote completo, o kappa de Fleiss foi 0,778. Sem as linhas `sem_release`, em 24 releases avaliáveis, o kappa foi 0,297.

A heurística de CFR(b), comparada ao consenso nas 24 releases avaliáveis, teve precisão 0,60, recall 0,30 e F1 0,40. Os números estão em `reports/validation/cfr_b_validation.json`. Linha sem predição não vira negativo.
