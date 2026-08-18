# Validação das RQ05, RQ06 e RQ07 — Lab01S02

Base analisada: **1000 repositórios únicos**.

## Hipóteses informais

- **RQ05:** espera-se que a maioria dos repositórios populares utilize linguagens presentes no top 10 do GitHub Octoverse 2024, com concentração em Python, JavaScript e TypeScript.
- **RQ06:** espera-se que repositórios populares apresentem uma proporção elevada de issues fechadas, embora projetos com manutenção ou crescimento intenso possam manter mais issues abertas.
- **RQ07:** espera-se que linguagens populares apresentem maior contribuição externa e mais releases; a frequência de atualização pode variar pouco entre projetos muito populares.

Fonte de linguagens populares: GitHub Octoverse 2024 - https://github.blog/news-insights/octoverse/octoverse-2024/.

## Integridade e valores ausentes

- Registros analisados: 1000
- Linguagem primária ausente: 87
- Linguagem presente no top 10 adotado: 724
- Repositórios sem issues, cuja razão não é calculável: 43
- Proporções inválidas ou inconsistentes: **0** (a validação interrompe a execução caso encontre alguma)

## RQ05 — Distribuição das linguagens

| Linguagem | Repositórios |
|---|---:|
| Python | 228 |
| TypeScript | 174 |
| JavaScript | 111 |
| Sem linguagem identificada | 87 |
| Go | 76 |
| Rust | 57 |
| C++ | 41 |
| Java | 41 |
| Jupyter Notebook | 24 |
| C | 21 |
| Shell | 20 |
| Ruby | 13 |
| HTML | 11 |
| Swift | 10 |
| Kotlin | 9 |
| C# | 8 |
| CSS | 8 |
| Dart | 6 |
| Vue | 6 |
| Markdown | 5 |
| Clojure | 4 |
| MDX | 4 |
| PHP | 4 |
| Vim Script | 3 |
| Zig | 3 |
| Astro | 2 |
| Dockerfile | 2 |
| Haskell | 2 |
| Makefile | 2 |
| PowerShell | 2 |
| Scala | 2 |
| TeX | 2 |
| Assembly | 1 |
| Batchfile | 1 |
| Blade | 1 |
| Elixir | 1 |
| Julia | 1 |
| LLVM | 1 |
| Lua | 1 |
| Nunjucks | 1 |
| Objective-C | 1 |
| Roff | 1 |
| Svelte | 1 |
| V | 1 |

## RQ06 — Proporção de issues fechadas

| Registros válidos | Mínimo | Q1 | Mediana | Média | Q3 | Máximo | Outliers IQR |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 957 | 7.69% | 70.42% | 87.61% | 80.23% | 96.84% | 100.00% | 38 |

Outliers de proporção (até 10 exibidos):

- `musistudio/claude-code-router`: 30.16%
- `geekcomputers/Python`: 29.89%
- `aymericdamien/TensorFlow-Examples`: 29.71%
- `Leonxlnx/taste-skill`: 29.27%
- `shiyu-coder/Kronos`: 29.21%
- `lencx/ChatGPT`: 29.06%
- `dair-ai/Prompt-Engineering-Guide`: 29.02%
- `jamiepine/voicebox`: 28.01%
- `CompVis/stable-diffusion`: 27.03%
- `paperclipai/paperclip`: 26.89%
- …

## RQ07 — Distribuições gerais

Outliers são definidos pelo método IQR: valores abaixo de `Q1 - 1,5 × IQR` ou acima de `Q3 + 1,5 × IQR`.

| Métrica | Mínimo | Q1 | Mediana | Média | Q3 | Máximo | Outliers |
|---|---:|---:|---:|---:|---:|---:|---:|
| PRs aceitas | 0 | 175 | 768 | 4233.82 | 3413.50 | 103313 | 124 |
| releases | 0 | 0 | 39 | 126.15 | 146.25 | 1000 | 92 |
| dias desde a atualizacao | 0 | 0 | 0 | 0.01 | 0 | 2 | 9 |

### Métricas agrupadas por linguagem

Grupos com menos de 5 repositórios são marcados como pequenos e devem ser interpretados com cautela.

| Linguagem | Repositórios | Mediana de PRs aceitas | Mediana de releases | Mediana de dias desde atualização | Grupo pequeno |
|---|---:|---:|---:|---:|---|
| Python | 228 | 559.50 | 20 | 0 | Não |
| TypeScript | 174 | 2000.50 | 133.50 | 0 | Não |
| JavaScript | 111 | 617 | 39 | 0 | Não |
| Sem linguagem identificada | 87 | 129 | 0 | 0 | Não |
| Go | 76 | 1694 | 139 | 0 | Não |
| Rust | 57 | 2495 | 90 | 0 | Não |
| C++ | 41 | 1156 | 46 | 0 | Não |
| Java | 41 | 941 | 55 | 0 | Não |
| Jupyter Notebook | 24 | 78 | 0 | 0 | Não |
| C | 21 | 294 | 45 | 0 | Não |
| Shell | 20 | 389.50 | 9.50 | 0 | Não |
| Ruby | 13 | 6253 | 28 | 0 | Não |
| HTML | 11 | 232 | 0 | 0 | Não |
| Swift | 10 | 702.50 | 38.50 | 0 | Não |
| Kotlin | 9 | 258 | 75 | 0 | Não |
| C# | 8 | 3113 | 126 | 0 | Não |
| CSS | 8 | 185.50 | 0 | 0 | Não |
| Dart | 6 | 592 | 35 | 0 | Não |
| Vue | 6 | 402 | 40.50 | 0 | Não |
| Markdown | 5 | 244 | 0 | 0 | Não |
| Clojure | 4 | 5161.50 | 119 | 0 | Sim |
| MDX | 4 | 380 | 1 | 0 | Sim |
| PHP | 4 | 10632.50 | 576 | 0 | Sim |
| Vim Script | 3 | 440 | 8 | 0 | Sim |
| Zig | 3 | 4480 | 20 | 0 | Sim |
| Astro | 2 | 1264.50 | 25.50 | 0 | Sim |
| Dockerfile | 2 | 383.50 | 0.50 | 0 | Sim |
| Haskell | 2 | 1073.50 | 94 | 0 | Sim |
| Makefile | 2 | 3010.50 | 169.50 | 0 | Sim |
| PowerShell | 2 | 792.50 | 41 | 0 | Sim |
| Scala | 2 | 5 | 0 | 0 | Sim |
| TeX | 2 | 19 | 3.50 | 0 | Sim |
| Assembly | 1 | 0 | 0 | 0 | Sim |
| Batchfile | 1 | 7 | 31 | 0 | Sim |
| Blade | 1 | 1710 | 227 | 0 | Sim |
| Elixir | 1 | 898 | 12 | 0 | Sim |
| Julia | 1 | 27795 | 203 | 0 | Sim |
| LLVM | 1 | 96964 | 159 | 0 | Sim |
| Lua | 1 | 6532 | 147 | 0 | Sim |
| Nunjucks | 1 | 485 | 0 | 0 | Sim |
| Objective-C | 1 | 710 | 40 | 0 | Sim |
| Roff | 1 | 1 | 0 | 0 | Sim |
| Svelte | 1 | 252 | 0 | 0 | Sim |
| V | 1 | 13791 | 304 | 0 | Sim |

Grupos pequenos identificados: Clojure (4), MDX (4), PHP (4), Vim Script (3), Zig (3), Astro (2), Dockerfile (2), Haskell (2), Makefile (2), PowerShell (2), Scala (2), TeX (2), Assembly (1), Batchfile (1), Blade (1), Elixir (1), Julia (1), LLVM (1), Lua (1), Nunjucks (1), Objective-C (1), Roff (1), Svelte (1), V (1).

### Possíveis outliers por métrica

#### PRs aceitas

- `firstcontributions/first-contributions`: 103313
- `llvm/llvm-project`: 96964
- `elastic/elasticsearch`: 95472
- `getsentry/sentry`: 91156
- `home-assistant/core`: 90088
- `rust-lang/rust`: 73573
- `grafana/grafana`: 69387
- `ClickHouse/ClickHouse`: 69089
- `kubernetes/kubernetes`: 65650
- `python/cpython`: 62642
- …

#### Releases

- `langchain-ai/langchain`: 1000
- `vercel/next.js`: 1000
- `ggml-org/llama.cpp`: 1000
- `electron/electron`: 1000
- `storybookjs/storybook`: 1000
- `home-assistant/core`: 1000
- `zed-industries/zed`: 1000
- `lobehub/lobehub`: 1000
- `ruvnet/ruflo`: 1000
- `withastro/astro`: 1000
- …

#### Dias desde a atualização

- `alibaba/easyexcel`: 2
- `lysine-dev/retrofit`: 1
- `aymericdamien/TensorFlow-Examples`: 1
- `bailicangdu/vue2-elm`: 1
- `babysor/MockingBird`: 1
- `nativefier/nativefier`: 1
- `Blankj/AndroidUtilCode`: 1
- `shadowsocks/shadowsocks`: 1
- `adobe/brackets`: 1

## Resultado da validação

Os 1000 registros passaram pelas verificações estruturais das RQ05, RQ06 e RQ07. Valores ausentes, distribuições, grupos pequenos e possíveis outliers estão registrados neste documento. As hipóteses são informais e deverão ser confrontadas com análises e visualizações na Sprint 3.
