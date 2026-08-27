# Revisao de fechamento da Lab01S03

Revisao executada em **26 de agosto de 2026** sobre a `main` apos a integracao
das Issues #33 a #38.

## Pipeline e visualizacoes

O comando abaixo foi executado em uma copia limpa do repositorio:

```bash
cd LAB1/code
python src/generate_visualizations.py
```

Resultado: **sucesso**, com o CSV consolidado de 1.000 repositorios validado e
as sete figuras geradas sem intervencao manual:

- RQ01: `reports/figures/rq01_idade.png`
- RQ02: `reports/figures/rq02_pull_requests.png`
- RQ03: `reports/figures/rq03_releases.png`
- RQ04: `reports/figures/rq04_atualizacao.png`
- RQ05: `reports/figures/rq05_linguagens.png`
- RQ06: `reports/figures/rq06_issues.png`
- RQ07: `reports/figures/rq07_linguagem_metricas.png`

As interpretacoes foram conferidas nos relatorios de RQ01/RQ02, RQ03/RQ04 e
RQ05/RQ06/RQ07. A validacao automatica confirmou formato PNG, arquivos nao
vazios, resolucao minima, titulos, eixos, unidades e correspondencia das
metricas com a base de 1.000 repositorios.

## Rastreabilidade

| Issue | Entrega | Assignee | Commit revisado | PR | Estado |
|---|---|---|---|---|---|
| #33 | Pipeline comum de visualizacao | `pedrorodriguesduarte` | `37ab2b6` | #40 | Done/closed |
| #34 | Visualizacoes RQ01 e RQ02 | `guilhermeas04` | `d198f55` | #43 | Done/closed |
| #35 | Visualizacoes RQ03 e RQ04 | `pedrorodriguesduarte` | `d11e54b` | #41 | Done/closed |
| #36 | Visualizacoes RQ05, RQ06 e RQ07 | `amandabicalh` | `c0d39fc` | #42 | Done/closed |
| #37 | Integracao das sete RQs | `guilhermeas04` | `a9cccc8` | #44 | Done/closed |
| #38 | Validacao automatica | `amandabicalh` | `a97ba55` | #45 | Done/closed |
| #39 | Revisao e snapshot final | `guilhermeas04` | este fechamento | a criar | Review/open |

## Auditoria do GitHub Project

- Project: **Kanban**, numero 3.
- Itens exportados: **20**.
- Itens em `Done`: **19**.
- Itens em `Review`: **1** (Issue #39).
- Itens em `Doing`: **0**, dentro do limite WIP de 3.
- Itens sem Assignee: **0**.
- Itens sem Status: **0**.
- Issues #33 a #38: revisadas, fechadas e em `Done`.
- Issue #39: mantida em `Review` ate a integracao deste fechamento.

## Snapshot final

O estado auditado foi exportado para:

`LAB1/data/snapshots/lab01s03-project-20260826T232421Z.csv`

O arquivo preserva timestamp, Project, identificador do item, Issue, titulo,
URL, repositorio, Assignees e Status no fechamento da Sprint 3.
