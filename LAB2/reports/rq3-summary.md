# LAB02 - RQ3

Analise das metricas estaticas dos 18 trials oficiais.
RQ3: o uso de assistente de IA altera a complexidade ciclomatica ou a duplicacao do codigo produzido?

## Completude das metricas

- Trials oficiais conferidos: 18
- Arquivos com status `ok`: 18
- Campos de metrica ausentes: 0
- Status diferente de `ok`: 0
- Completude automatica: sim

## Tabelas finais por tratamento

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

## Wilcoxon bicaudal e correcao de Holm

| Metrica | n pares | W+ | p exato | Limiar Holm | Rejeita H0 | Status |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| LOC | 3 | 3.0 | 1.0 | 0.0125 | False | ok |
| CC media | 3 | 2.0 | 1.0 | 0.016667 | False | ok |
| CC maxima | 3 | 2.0 | 1.0 | 0.025 | False | ok |
| Duplicacao (%) | 0 |  |  |  | False | not_applicable |
| Indice de manutenibilidade | 3 | 3.0 | 1.0 | 0.05 | False | ok |

## Casos extremos

| Metrica | Minimo | Maximo |
| --- | --- | --- |
| LOC | P03-K02-AI (12.0) | P02-K05-MANUAL (47.0) |
| CC media | P01-K03-AI (5.0) | P02-K05-MANUAL (27.0) |
| CC maxima | P01-K03-AI (6.0) | P02-K05-MANUAL (27.0) |
| Duplicacao (%) | P01-K01-AI (0.0) | P01-K01-AI (0.0) |
| Indice de manutenibilidade | P01-K04-MANUAL (42.33) | P03-K02-AI (63.438) |

## Interpretacao da RQ3

**Complexidade.** A mediana de CC media foi 13.0 com IA e 14.0 no manual; a CC maxima seguiu o mesmo padrao aproximado. A diferenca descritiva e pequena e nao se sustenta no Wilcoxon bicaudal com N=3.

**Duplicacao.** Ambos os tratamentos ficaram com mediana 0.0% (manual 0.0%). Sem variacao, o teste pareado dessa metrica fica `not_applicable`.

**LOC (controle).** Mediana de 32.0 linhas com IA contra 25.0 no manual. O codigo com IA tende a ser um pouco mais verboso; por isso qualquer leitura de complexidade precisa considerar LOC, nao so o valor absoluto de CC.

**Manutenibilidade.** MI mediano 50.727 com IA e 50.874 no manual, praticamente equivalentes. O indice composto nao aponta ganho estrutural claro de um tratamento sobre o outro.

Nenhuma metrica rejeitou H0 apos Holm. No conjunto, a evidencia disponivel nao indica alteracao robusta de complexidade ou duplicacao pelo uso de IA neste experimento.

## Limitacoes

- N=3 pares; Wilcoxon exato dificilmente atinge p < 0,05.
- LOC e metrica de controle: codigo com IA pode ser mais verboso e isso afeta a leitura da complexidade.
- Duplicacao zerada nos dois tratamentos limita o Wilcoxon dessa metrica.
- Codigo incompleto pode parecer artificialmente simples; subset 100% green tem 18 trials.
- Metricas ausentes nao foram imputadas como zero.
