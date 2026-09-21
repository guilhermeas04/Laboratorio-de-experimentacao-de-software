# LAB02 - RQ1/RQ2

Analise gerada a partir dos 18 trials oficiais do contrabalanceamento.
O arquivo `P01-K01-MANUAL.json` nao faz parte do desenho oficial e foi ignorado.

## Estatisticas descritivas

| Tratamento | Metrica | n | Mediana | IQR | Min | Max |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| with_ai | Tempo (s) | 9 | 18.073 | 36.9 | 0.135 | 308.704 |
| with_ai | Taxa de sucesso (%) | 9 | 100.0 | 0.0 | 100.0 | 100.0 |
| with_ai | Testes falhando | 9 | 0.0 | 0.0 | 0.0 | 0.0 |
| manual | Tempo (s) | 9 | 24.712 | 375.137 | 0.143 | 487.28 |
| manual | Taxa de sucesso (%) | 9 | 100.0 | 0.0 | 100.0 | 100.0 |
| manual | Testes falhando | 9 | 0.0 | 0.0 | 0.0 | 0.0 |

## Testes de Wilcoxon

| RQ | Metrica pareada | Alternativa | n | W+ | p exato | Status |
| --- | --- | --- | ---: | ---: | ---: | --- |
| RQ1 | Mediana de tempo com IA - manual | with_ai < manual | 2 | 0 | 0.25 | ok |
| RQ2 | Mediana de taxa de sucesso com IA - manual | with_ai > manual | 0 |  |  | not_applicable |
| RQ2 | Mediana de testes falhando com IA - manual | with_ai < manual | 0 |  |  | not_applicable |

## Interpretacao curta

**RQ1.** A mediana de tempo com IA foi 18.073s e a manual foi 24.712s; descritivamente, o tempo com IA foi menor. O Wilcoxon exato retornou status `ok` e p=0.25; com N=3, isso nao deve ser apresentado como evidencia conclusiva.

**RQ2.** A mediana de taxa de sucesso foi 100.0% com IA e 100.0% no manual. Os testes falhando tiveram status `not_applicable` no Wilcoxon, indicando que empates ou ausencia de defeitos limitam a comparacao inferencial.

## Limitacoes

- O desenho possui apenas tres participantes; resultados inferenciais devem ser tratados como exploratorios.
- Com tres pares, o menor p-valor unilateral possivel no Wilcoxon exato e 0.125.
- A comparacao pareada usa medianas por participante para manter o desenho within-subject.
