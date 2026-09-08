# LAB02 — Assistentes de IA vs. codificação manual

Este diretório reúne o experimento controlado que compara a resolução de katas
com e sem assistente de IA. A preparação segue um desenho crossover
within-subject, com seis katas e time-box máximo de 35 minutos por trial.

## Estrutura

```text
LAB2/
├── code/                  # pacote Python, dependências e testes
│   ├── src/lab02/         # contrato e validação dos dados
│   └── tests/             # testes automatizados
├── data/
│   ├── examples/          # registros fictícios para validar o ambiente
│   ├── sessions/          # estado transitório dos cronômetros ativos
│   ├── raw/               # registros imutáveis dos trials reais
│   └── processed/         # dados consolidados para análise
├── docs/                  # desenho e protocolo experimental
└── reports/               # resultados, tabelas e figuras
```

Os diretórios `raw` e `processed` são separados para impedir que a limpeza dos
dados altere os registros originais do experimento. O exemplo versionado é
fictício e não deve ser incluído nas análises.

## Ambiente reproduzível

Versão adotada: **Python 3.13.7**. A versão também está registrada em
`code/.python-version`, e as dependências possuem versões exatas no
`code/requirements-dev.txt`.

No PowerShell, a partir da raiz do repositório:

```powershell
cd LAB2/code
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## Validação

Execute a suíte completa:

```powershell
cd LAB2/code
python -m pytest
```

Valide o registro fictício diretamente:

```powershell
cd LAB2/code
python -m lab02.validate_record ../data/examples/trial-valid.json
```

O comando termina com código `0` para um registro válido e com código diferente
de zero quando encontra dados inválidos.

## Cronometragem e coleta dos trials

A issue #48 fornece a CLI `lab02-trial`, com três operações. Inicie o trial
imediatamente antes de apresentar o enunciado ao participante:

```powershell
lab02-trial start `
  --trial-id P01-K01-AI `
  --participant participant-01 `
  --kata-id kata-01 `
  --treatment with_ai `
  --execution-order 1 `
  --assistant-name ChatGPT `
  --assistant-version "versão registrada no protocolo"
```

Consulte o tempo sem alterar o registro:

```powershell
lab02-trial status --trial-id P01-K01-AI
```

Encerre assim que todos os testes passarem ou imediatamente ao atingir 35
minutos:

```powershell
lab02-trial finish `
  --trial-id P01-K01-AI `
  --tests-total 12 `
  --tests-passing 12 `
  --prompt-count 4
```

No tratamento manual, omita `--assistant-name`, `--assistant-version` e
`--prompt-count`. A CLI calcula a taxa de sucesso, aplica a censura e grava o
resultado uma única vez em `data/raw/<trial-id>.json`. Registros existentes não
são sobrescritos.

O encerramento incompleto antes do limite é recusado. Se todos os testes forem
informados como aprovados somente depois do limite, a CLI também recusa o
registro, pois não seria possível determinar honestamente o `time-to-green`.
Consulte o protocolo detalhado em `docs/coleta-trials.md`.

## Métricas estáticas (RQ3)

A issue #49 adiciona o comando `lab02-metrics`, que analisa o código final de um
trial com Radon (LOC/SLOC, complexidade ciclomática e índice de
manutenibilidade) e com o detector de duplicação configurado em
`code/static_metrics.toml`.

```powershell
cd LAB2/code
lab02-metrics `
  --trial-id P01-K01-AI `
  --source caminho\para\codigo_final
```

A saída JSON fica em `data/processed/metrics-<trial-id>.json` e contém os
campos `loc`, `cyclomatic_complexity_mean`, `cyclomatic_complexity_max`,
`duplication_percentage` e `maintainability_index`, prontos para integração ao
registro da #47. Arquivos vazios, código inválido ou origem ausente produzem
`status` explícito com métricas `null` — nunca zero silencioso.

## Contrato dos dados

Cada trial deve conter identificação, participante, kata, tratamento, ordem,
horários, duração, censura, resultados dos testes e métricas estruturais. As
métricas estruturais podem permanecer nulas até sua coleta pela pipeline da
issue #49.

Regras centrais:

- `elapsed_seconds` nunca ultrapassa 2.100 segundos;
- trial censurado termina em 2.100 segundos, não possui `time_to_green_seconds`
  e ainda tem pelo menos um teste falhando;
- trial concluído possui todos os testes passando e registra
  `time_to_green_seconds` igual à duração;
- `success_rate` é a razão entre testes passando e testes totais;
- tratamento com IA identifica assistente e versão; tratamento manual não pode
  preencher esses campos;
- percentuais ficam entre 0 e 100 e métricas de contagem não são negativas.

O contrato executável está em `code/src/lab02/trial_record.py`. Mudanças no
formato devem atualizar simultaneamente o módulo, os testes, o exemplo e esta
documentação.

## Rastreabilidade

Esta fundação corresponde à issue #47. Commits e pull requests relacionados
ao cronômetro e à coleta devem mencionar `#48`. Commits e pull requests da
pipeline de métricas estáticas devem mencionar `#49`.
