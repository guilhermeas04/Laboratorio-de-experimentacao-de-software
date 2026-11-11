# LAB04S02: Q3, violação de pressupostos

## Situações escolhidas

A Q3 repete as análises de erro tipo I (Q1) e de poder (Q2) em duas situações
não ideais, já registradas em `config/simulation.json`:

| Situação | Configuração | Motivo no cenário P1 |
|---|---|---|
| `small_sample` | 8 PRs por grupo | Repositórios pequenos ou recortes curtos de tempo produzem poucos PRs mesclados por grupo. |
| `extreme_outlier` | 30 PRs por grupo, 5% das observações multiplicadas por 20 | PRs esquecidos por semanas aparecem na amostra real e geram caudas muito longas. |

As duas situações mantêm a base lognormal da situação ideal. Os dados já são
muito assimétricos (sigma de log de 1,70 no grupo humano). Assim, a
assimetria está presente em todas as situações, e a Q3 isola o efeito de
reduzir a amostra e de adicionar outliers.

## Impacto esperado

- **Amostra pequena:** o t de Welch depende da aproximação pelo Teorema Central
  do Limite, que é fraca com n = 8 e dados lognormais. O Mann-Whitney tem
  distribuição discreta de postos, o que pode deixá-lo conservador. Os dois
  testes devem perder poder.
- **Outliers:** valores multiplicados por 20 inflam a variância amostral e
  reduzem a estatística t, então o Welch deve ficar conservador e perder poder.
  O Mann-Whitney usa postos, então um outlier conta apenas como a maior
  observação e o teste deve ser pouco afetado.

## Procedimento

Para cada situação:

1. Q1: gerar 10.000 conjuntos com H0 verdadeira (mesma distribuição nos dois
   grupos), aplicar Welch e Mann-Whitney e medir a proporção de p < 0,05.
2. Q2: repetir para os efeitos 0; 0,25; 0,5; 1 e 2 horas somados ao grupo
   humano e medir a proporção de rejeições.
3. Usar semente derivada de `random_seed = 42`, com deslocamento fixo por
   situação e por efeito, para que cada curva seja reproduzível de forma
   independente.

Um desvio de erro tipo I é classificado como liberal ou conservador quando sai
da margem de Monte Carlo de ±1,96·√(0,05·0,95/10.000) ≈ ±0,43 ponto percentual.

## Execução

```powershell
$env:PYTHONPATH = "LAB4/src"
python -m lab04_hypothesis.s02_report
```

O comando reaproveita `data/processed/q1_results.csv` e `q2_results.csv` quando
eles têm o mesmo número de repetições. Caso contrário, executa Q1/Q2 pelo
`simulation_runner` da issue #134.

## Saídas

| Arquivo | Conteúdo |
|---|---|
| `data/processed/q3_type_i_results.csv` | Erro tipo I da Q3 |
| `data/processed/q3_power_results.csv` | Poder da Q3 |
| `data/processed/q3_summary.json` | Resultados da Q3 e interpretação |
| `reports/tables/g3_type_i_error.csv` | Dados do G3 (ideal + Q3) |
| `reports/tables/g4_power.csv` | Dados do G4 (ideal + Q3) |
| `reports/tables/g3_g4_interpretation.json` | Textos de 2 a 4 frases para o dashboard |
| `reports/figures/g3_type_i_error.png` | G3 |
| `reports/figures/g4_power.png` | G4 |

As tabelas usam as mesmas colunas da Q1/Q2 (`question`, `situation`,
`test_name`, `effect_hours`, `replications`, `rejections`, `rejection_rate` ou
`power`, `alpha`), então o dashboard pode filtrar por `situation` sem
tratamento extra.

## Resultados (10.000 repetições, semente 42)

Erro tipo I (proporção de p < 0,05 com H0 verdadeira):

| Situação | t de Welch | Mann-Whitney |
|---|---|---|
| Ideal (n = 30) | 2,28% | 4,56% |
| Amostra pequena (n = 8) | 1,16% | 4,95% |
| Outliers (5% × 20) | 1,65% | 4,88% |

Poder no maior efeito (2 h):

| Situação | t de Welch | Mann-Whitney |
|---|---|---|
| Ideal (n = 30) | 38,2% | 99,4% |
| Amostra pequena (n = 8) | 28,0% | 61,0% |
| Outliers (5% × 20) | 19,4% | 98,5% |

## Interpretação

Os textos abaixo são gerados por `interpretation.py` a partir dos resultados e
também ficam em `reports/tables/g3_g4_interpretation.json`.

**G3 — Erro tipo I.** O Mann-Whitney teve erro tipo I de 4,56% na situação
ideal, 4,95% na amostra pequena, 4,88% na presença de outliers e foi
conservador na situação ideal e adequado nas demais. O t de Welch teve erro
tipo I de 2,28% na situação ideal, 1,16% na amostra pequena, 1,65% na presença
de outliers e foi conservador em todas as situações. O desvio do Welch vem da
assimetria lognormal e das caudas longas, que inflam a variância amostral e
encolhem a estatística t, enquanto o Mann-Whitney usa postos e quase não sente
valores extremos.

**G4 — Poder.** Na situação ideal, o Mann-Whitney teve maior poder, chegando a
99,4% contra 38,2% do t de Welch no efeito de 2,00 h. A diferença cresceu com o
efeito, de 23,8% em 0,25 h para 61,2% em 2,00 h. A vantagem não mudou de lado
em nenhuma situação: a diferença média foi maior na presença de outliers
(56,7%) e menor na amostra pequena (21,4%), onde os dois testes perdem poder.

## Conclusão estatística da Q3

Os dados de tempo de merge não satisfazem a suposição prática do Welch, que
depende de médias aproximadamente normais. Com caudas lognormais longas, o
Welch não fica liberal: ele fica conservador e perde muito poder, porque a
variância amostral domina a estatística. O Mann-Whitney mantém o erro tipo I
perto de 5% e tem maior poder em todas as situações. Por isso, ele é o teste
recomendado para este cenário. A amostra pequena é a única condição que
reduz bastante o poder do Mann-Whitney, mas mesmo nela ele continua à frente.
