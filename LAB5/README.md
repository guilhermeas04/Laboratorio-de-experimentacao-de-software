# LAB05 — Experimento em software real

Estrutura inicial para o experimento final sobre um software real, em operação
e de alto impacto. O objeto de estudo, a pergunta de pesquisa e o desenho serão
definidos pelo grupo na proposta.

## Estrutura

```text
LAB5/
├── config/                 # parâmetros do estudo e da coleta
├── data/
│   ├── raw/                # dados brutos e registros originais
│   ├── interim/            # dados validados e transformados
│   └── processed/          # datasets finais para a análise
├── docs/                   # proposta, método, ética e documentação final
├── notebooks/              # exploração e análises auxiliares
├── reports/
│   ├── figures/            # visualizações e gráficos finais
│   └── tables/             # tabelas e resultados estatísticos
├── dashboard/              # dashboard ou visualização final, se aplicável
├── src/lab05_real_software/ # coleta, validação, análise e impacto
└── tests/                  # testes automatizados e validações
```

O diretório `data/raw` deve preservar os registros originais. Dados pessoais,
credenciais e informações que não possam ser compartilhadas não devem ser
versionados.

## Sprints

- `Lab05S01`: proposta, evidências do software, GQM, categorias da pesquisa,
  plano de coleta/análise e coleta piloto.
- `Lab05S02`: coleta completa, validação, análise e ameaças à validade.
- `Lab05S03`: impacto, conclusões, limitações e rascunhos do documento e da
  apresentação.
- Documento final e apresentação: formato livre, conforme o enunciado.

## Critérios do estudo

O software escolhido deve ser real, estar em operação e ter alto impacto,
sempre com evidências e fontes. A coleta deve respeitar os termos de uso,
`robots.txt`, o limite de uma requisição por segundo para medições externas e
as regras de ética descritas no enunciado.

## Piloto PostgreSQL

Prepare as imagens oficiais antes da coleta. Execute a partir da raiz do
repositório, em PowerShell.

```powershell
docker pull postgres:15.20
docker pull postgres:17.12
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.postgres_pilot --blocks 2
python -m pytest -q LAB5/tests
```

Cada rodada cria um contêiner descartável sem rede, com 1 CPU e 512 MB de
memória. O roteiro carrega 100 mil pedidos sintéticos, aquece uma consulta de
soma por cliente e repete a consulta com `EXPLAIN ANALYZE`. As versões rodam
em sequência e a ordem é invertida a cada bloco.

Os JSONs ficam em `LAB5/data/raw/` por padrão. O campo `stdout` contém a
versão confirmada pelo servidor e o plano em JSON, com o tempo de execução
no servidor em `Execution Time` (ms). `duration_ms` inclui a inicialização
do cliente. Os registros com rótulo `pilot-local` correspondem à verificação
inicial do coletor. O piloto com PostgreSQL valida a instrumentação de
latência para uma consulta. Throughput, CPU e memória ficam para a próxima
etapa de instrumentação.

## Análise e impacto do piloto

```powershell
python -m pip install -r LAB5/requirements.txt
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.pilot_metrics
python -m lab05_real_software.analysis --metrics LAB5/data/interim/pilot_metrics.csv --tables-dir LAB5/reports/tables
python -m lab05_real_software.impact --metrics LAB5/data/interim/pilot_metrics.csv --tables-dir LAB5/reports/tables --figures-dir LAB5/reports/figures
```

O efeito pareado usa a média das diferenças por bloco dividida pelo desvio
padrão dessas diferenças (Cohen's d_z). Com menos de dois pares completos
ou desvio zero, o tamanho de efeito fica vazio. A projeção anual soma a
diferença de tempo de execução no servidor sob o volume hipotético de consultas.
Os dois blocos do piloto servem para verificar a instrumentação e o fluxo de análise.

## Coleta completa

O [desenho da Sprint 2](docs/desenho-lab05s02.md) fixa a configuração,
as métricas e o plano de análise. Ele inclui o comando de verificação da
instrumentação com PostgreSQL 15.20 e 17.12.

## Validação da coleta completa

A campanha completa é validada e transformada sem alterar os JSONs brutos:

```powershell
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.s02_dataset LAB5/data/raw/s02/lab05s02-20261121-01 --output-dir LAB5/data/processed
python -m pytest -q LAB5/tests/test_s02_dataset.py LAB5/tests/test_validator.py LAB5/tests/test_postgres_campaign.py
```

O comando gera em `LAB5/data/processed/` um CSV versionado por campanha, um relatório JSON e um relatório Markdown com rastreabilidade até os arquivos brutos, ausências por métrica, falhas e exclusões. O contrato atualizado está em `LAB5/docs/data-dictionary-lab05s02.md`; ausência não é preenchida por imputação.

## Análise descritiva da coleta completa (#153)

```powershell
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.s02_descriptive --dataset LAB5/data/processed/lab05s02-20261121-01_validated.csv
python -m pytest -q LAB5/tests/test_s02_descriptive.py
```

O comando lê o dataset validado, preserva o `block` e o caminho bruto em
`source`, e gera:

- tabelas em `LAB5/reports/tables/s02_*`;
- gráficos em `LAB5/reports/figures/s02_*`;
- critérios de agregação em `LAB5/docs/analise-descritiva-lab05s02.md`.

Ausentes entram em `n_missing` e nunca são imputados como zero.

## Diagnósticos de validade da coleta completa (#154)

```powershell
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.s02_validity
python -m pytest -q LAB5/tests/test_s02_validity.py
```

A execução verifica configuração e imagens dos registros brutos contra o manifesto e gera diagnósticos de sensibilidade por ordem, estabilidade entre blocos, média/mediana e política de exclusões em `LAB5/reports/validity/`. A avaliação das ameaças, evidências, mitigações e riscos residuais está em `LAB5/docs/validade-lab05s02.md`.

## Testes pareados e tamanho de efeito (#155)

```powershell
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.s02_inference --dataset LAB5/data/processed/lab05s02-20261121-01_validated.csv
python -m pytest -q LAB5/tests/test_s02_inference.py
```

O comando aplica o contraste pareado pré-especificado (`customer_total` / `query_latency_ms`), verifica pressupostos, estima a diferença com IC 95% e o Cohen `d_z`, interpreta a relevância prática contra o limiar de 10% e trata métricas secundárias com ajuste de Holm. Artefatos versionados:

- `LAB5/reports/tables/s02_paired_primary_differences.csv`
- `LAB5/reports/tables/s02_paired_primary_inference.json`
- `LAB5/reports/tables/s02_paired_secondary_inference.csv`
- `LAB5/reports/tables/s02_paired_inference_summary.json`
- `LAB5/docs/inferencia-pareada-lab05s02.md`

Pares incompletos, variância zero e amostra pequena (< 2 pares) são registrados como inferência insuficiente.
