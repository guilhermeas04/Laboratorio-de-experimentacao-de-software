# Inferência pareada — LAB05S02

Contraste pré-especificado no desenho da Sprint 2 (#150) e executado para a issue #155.

- versões: `15.20` (A) versus `17.12` (B);
- cenário/métrica primários: `customer_total` / `query_latency_ms`;
- unidade de análise: bloco pareado;
- H0: diferença média pareada igual a zero; alternativa bilateral; alfa = 0,05;
- teste confirmatório: t pareado, quando os pressupostos forem sustentáveis;
- tamanho de efeito: Cohen `d_z` = média(diferenças) / desvio-padrão(diferenças);
- ganho mínimo de relevância prática: redução relativa de 10% da média da versão A;
- demais métricas/cenários: exploratórios, com ajuste de Holm.

## Resultado primário

- pares completos: **24**;
- média A (`15.20`): **0,410 ms**; média B (`17.12`): **0,390 ms**;
- diferença média A−B: **0,0201 ms**;
- IC 95%: **[0,0078; 0,0324]**;
- estatística t (df = 23): **3,37**; p-valor: **0,0026** (rejeita H0 ao alfa 0,05);
- Shapiro–Wilk nas diferenças: p = **0,0052** → pressuposto de normalidade **questionável**; status `assumption_warning`;
- Wilcoxon exploratório (não substitui o contraste pré-registrado): p = **0,0017**;
- Cohen `d_z`: **0,69**;
- relevância prática (≥ 10%): **não atingida** (mudança relativa observada ≈ **4,9%**).

## Métricas secundárias

Os contrastes exploratórios e os p-valores ajustados por Holm estão em
`reports/tables/s02_paired_secondary_inference.csv`. Eles não alteram a decisão
confirmatória do contraste primário.

## Casos de inferência insuficiente

O código registra `inference_status = insufficient` quando:

- há menos de dois pares completos;
- a variância das diferenças é zero (teste t e `d_z` indefinidos).

Pares com valor ausente em qualquer lado são excluídos antes do contraste.

## Reprodução

```powershell
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.s02_inference --dataset LAB5/data/processed/lab05s02-20261121-01_validated.csv
python -m pytest -q LAB5/tests/test_s02_inference.py
```

## Leitura

Há evidência estatística de diferença pareada na latência primária, com ressalva
de normalidade e tamanho de efeito moderado. A redução relativa observada fica
abaixo do limiar pré-especificado de 10%, então a relevância prática definida no
desenho **não** é atingida neste contraste.
