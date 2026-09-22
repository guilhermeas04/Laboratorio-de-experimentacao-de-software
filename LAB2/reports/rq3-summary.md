# LAB02 - RQ3

Analise das metricas estaticas dos 18 trials oficiais.
RQ3: o uso de assistente de IA altera a complexidade ciclomatica ou a duplicacao do codigo produzido?

## Completude

- Trials oficiais: 18
- Com status ok: 18
- Metricas ausentes: 0
- Status diferente de ok: 0

## Estatisticas descritivas

| Tratamento | Metrica | n | Mediana | IQR | Min | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| with_ai | LOC | 9 | 32.0 | 14.5 | 12.0 | 40.0 |
| with_ai | CC media | 9 | 13.0 | 14.5 | 5.0 | 25.0 |
| with_ai | CC maxima | 9 | 13.0 | 13.5 | 6.0 | 25.0 |
| with_ai | Duplicacao (%) | 9 | 0.0 | 0.0 | 0.0 | 0.0 |
| with_ai | Indice de manutenibilidade | 9 | 50.727 | 5.223 | 43.633 | 63.438 |
| manual | LOC | 9 | 25.0 | 25.5 | 13.0 | 47.0 |
| manual | CC media | 9 | 14.0 | 13.5 | 6.0 | 27.0 |
| manual | CC maxima | 9 | 14.0 | 13.5 | 6.0 | 27.0 |
| manual | Duplicacao (%) | 9 | 0.0 | 0.0 | 0.0 | 0.0 |
| manual | Indice de manutenibilidade | 9 | 50.874 | 12.9245 | 42.33 | 63.127 |

## Wilcoxon bicaudal e Holm

| Metrica | n pares | W+ | p exato | Limiar Holm | Rejeita H0 | Status |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| LOC | 3 | 3.0 | 1.0 | 0.0125 | False | ok |
| CC media | 3 | 2.0 | 1.0 | 0.016667 | False | ok |
| CC maxima | 3 | 2.0 | 1.0 | 0.025 | False | ok |
| Duplicacao (%) | 0 |  |  |  | False | not_applicable |
| Indice de manutenibilidade | 3 | 3.0 | 1.0 | 0.05 | False | ok |

## Interpretacao curta

**RQ3.** Comparando medianas, LOC com IA foi 32.0 frente a 25.0 no manual; CC media 13.0 vs 14.0; duplicacao 0.0% vs 0.0%; MI 50.727 vs 50.874. Nenhuma metrica rejeitou H0 apos Holm. Com amostra pequena, a leitura deve priorizar as medianas/IQR e o efeito de LOC sobre complexidade, sem tratar p-valor como prova conclusiva.

## Limitacoes

- N=3 pares; Wilcoxon exato dificilmente atinge p < 0,05.
- LOC controla verbosidade: maior LOC pode elevar CC sem piorar o desenho.
- Codigo incompleto pode parecer artificialmente simples; ver subset 100% green.
- Metricas ausentes nao foram imputadas como zero.
