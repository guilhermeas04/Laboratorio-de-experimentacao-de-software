# Ameaças à validade — LAB05S02 (#154)

## Escopo e reprodução

Os diagnósticos usam a campanha validada `lab05s02-20261121-01`, seu manifesto, os 96 JSONs brutos e o CSV validado. Para reproduzir a saída a partir da raiz do repositório, com as dependências de `LAB5/requirements.txt` instaladas:

```powershell
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.s02_validity
python -m pytest -q LAB5/tests/test_s02_validity.py
```

As saídas versionadas ficam em `LAB5/reports/validity/lab05s02-20261121-01_validity.json` e `LAB5/reports/validity/lab05s02-20261121-01_validity.csv`. O JSON resume consistência, falhas, exclusões e a interpretação; o CSV preserva estimativas por cenário, métrica, ordem e subconjunto de blocos. O teste altera a configuração de uma rodada bruta e verifica que o diagnóstico detecta a divergência.

## Diagnósticos observados

O manifesto registra 96 rodadas planejadas, 96 bem-sucedidas, 24 blocos aceitos, nenhuma tentativa não aceita e nenhum desvio. As 96 configurações dos registros brutos coincidem com o manifesto e as imagens correspondem às versões registradas. O relatório de qualidade contém zero exclusões, zero métricas ausentes e zero pares incompletos. Portanto, a sensibilidade a exclusões não pode estimar um efeito de exclusões que não ocorreram; a tabela reproduz a regra estrita de remover blocos com tentativas não aceitas e confirma que, nesta campanha, a estimativa permanece igual.

A análise primária pré-especificada é a latência de `customer_total`, com redução média mínima de 10% como limiar de relevância prática. A diferença entre as médias é uma redução de aproximadamente 4,90% para PostgreSQL 17.12 frente a 15.20; portanto, o limiar prático não é atingido. A estratificação por ordem resulta em aproximadamente 5,54% quando 15.20 roda primeiro e 4,25% quando 17.12 roda primeiro. A primeira metade dos blocos tem cerca de 2,81% e a segunda, 6,98%. Esses estratos mantêm a estimativa abaixo do limiar de 10%; são diagnósticos descritivos, não testes confirmatórios.

## Ameaças

| Tipo | Evidência | Mitigação aplicada | Risco residual |
|---|---|---|---|
| Conclusão | A redução média primária observada é aproximadamente 4,90%, abaixo do limiar prático de 10%. A estimativa varia entre ordem (4,25%–5,54%) e metades de bloco (2,81%–6,98%). | Comparação pareada em 24 blocos; sequência balanceada (12 por ordem); média e mediana, estratos por ordem, metades e diagnóstico leave-one-block-out são publicados. A análise inferencial prevista no protocolo deve ser consultada antes de qualquer alegação confirmatória. | Variação entre blocos e capacidade limitada para detectar efeitos pequenos; não se conclui equivalência nem ausência de efeito. A classificação de relevância prática depende do limiar pré-definido. |
| Interna | Execuções sequenciais em um único host podem sofrer variação temporal, temperatura, processos concorrentes ou efeitos residuais de cache. Cada rodada usa um contêiner novo e parâmetros controlados; a ordem das versões é balanceada e o manifesto não registra desvios. | Mesmo host, limites de CPU/memória, buffers, dataset e carga por rodada; versões comparadas dentro do mesmo bloco; diagnóstico por ordem e por posição dos blocos. | O host não é dedicado e a coleta não mede nem elimina toda interferência temporal. A comparação não isola cada mecanismo causal de diferenças entre versões. |
| Construto | `query_latency_ms` é a mediana de cinco tempos de execução no servidor antes da janela concorrente. TPS e latência do cliente vêm do pgbench durante carga concorrente. CPU do cgroup inclui servidor, pgbench e monitoramento; memória inclui memória contabilizada pelo kernel/cache. | Definições, unidades e janelas estão no desenho e catálogo de métricas; medições são mantidas separadas; consistência e configuração são verificadas contra os registros brutos. | As métricas são proxies distintos de desempenho e não representam, isoladamente, experiência percebida, custo operacional ou eficiência de uma aplicação completa. |
| Externa | Foram testadas somente PostgreSQL 15.20 e 17.12, duas consultas SQL, tabela sintética determinística de 100 mil linhas, quatro clientes e um host Windows com Docker/Linux cgroup. | Delimitação explícita do estudo; mesma carga e configuração para as duas versões; brutos e identificadores são preservados para auditoria. | Não há amostragem de dados, esquemas, consultas, versões, hardware, sistemas operacionais, concorrência ou tráfego de produção. Generalização para produção não é sustentada por esta coleta. |

## Limite da conclusão

As metades usam os blocos previstos no manifesto. Se faltarem pares
utilizáveis, o diagnóstico marca a interpretação como indeterminada.
A leitura conjunta com o teste inferencial e seu intervalo de confiança
fica pendente da issue #155.

Os resultados descrevem as duas versões e os cenários `customer_total` e `range_summary` sob o dataset sintético e o ambiente documentado. Não sustentam uma recomendação geral de upgrade, uma estimativa de desempenho em produção ou uma afirmação causal além deste protocolo. Os diagnósticos de sensibilidade servem para mostrar robustez e dependência de escolhas analíticas; não substituem o teste inferencial previsto nem corrigem limites de validade externa.
