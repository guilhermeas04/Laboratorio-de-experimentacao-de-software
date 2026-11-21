# LAB05S02 — Desenho e instrumentação

Comparamos PostgreSQL 15.20 e 17.12 em instâncias locais descartáveis.
A configuração versionada está em [collection-s02.json](../config/collection-s02.json).
Os cenários são uma agregação seletiva por cliente, típica de uma consulta
operacional, e um resumo agrupado de uma faixa de pedidos, típico de uma
consulta analítica. Ambos usam os mesmos 100 mil pedidos sintéticos, gerados
deterministicamente a partir da semente 150. Os contêineres têm a mesma
configuração explícita de CPU, memória e buffers, sem rede.

## Desenho e análise

- Um bloco contém as duas versões para cada cenário na mesma máquina.
  Cada rodada usa uma instância nova, com carga e aquecimento iguais.
  A semente embaralha 12 blocos de cada ordem. Os dois cenários são executados
  na mesma ordem em cada versão. As repetições internas compõem a medida da
  rodada. A comparação pareada usa o bloco como unidade.
- A métrica primária é a latência no servidor em `customer_total`. A
  hipótese nula é diferença média pareada igual a zero e a alternativa é
  bilateral, com alfa de 0,05. Uma redução média equivalente a pelo menos
  10% da média do PostgreSQL 15 foi escolhida como limiar de relevância
  prática para este estudo. Reportar a diferença e o intervalo de 95%,
  com teste t pareado quando os pressupostos forem sustentáveis. Os
  demais resultados são exploratórios.
- Serão coletados 24 blocos, com 12 por ordem, dentro do orçamento da
  sprint. O piloto teve somente dois pares, com desvio das diferenças de
  aproximadamente 0,14 ms, medidos com outra instrumentação. Se esse
  desvio se mantivesse, o erro padrão com 24 pares seria aproximadamente
  0,029 ms. O piloto oferece precisão limitada para planejar a amostra e o
  desenho pode ter baixa capacidade de detectar a redução de 10%.
- Preservar todas as tentativas. Excluir da comparação de uma métrica os
  blocos sem par completo, com falha de execução, versão divergente ou
  configuração divergente. Registrar os motivos e as contagens. Manter
  valores extremos válidos e interromper a coleta se o ambiente mudar.

## Métricas

| Campo | Medição por rodada |
|---|---|
| `query_latency_ms` | Mediana de cinco valores de `Execution Time` do `EXPLAIN ANALYZE`, após aquecimento e antes da janela concorrente. |
| `throughput_queries_per_second` | TPS do pgbench sem o tempo de conexão inicial. Cada transação executa uma consulta. A fase medida dura 15 s, após 5 s de aquecimento com quatro clientes. |
| `cpu_percent` | Delta do contador de CPU do cgroup (`usage_usec` em v2 ou `cpuacct.usage` convertido de nanossegundos em v1), dividido pela janela amostrada e pela cota de CPU, em porcentagem. |
| `memory_mb` | Média aritmética de `memory.current` em v2 ou `memory.usage_in_bytes` em v1, em MB decimais, com amostras aproximadamente a cada segundo e nos limites da janela. |
| `client_latency_ms` | Latência média reportada pelo pgbench durante a carga concorrente, incluindo a interação com o cliente. |

As métricas de contêiner incluem o servidor, o pgbench e o custo do
monitoramento. A janela de recursos envolve a execução do pgbench e pode
ser ligeiramente maior que a janela usada no TPS. A memória do cgroup
inclui a memória contabilizada pelo kernel, inclusive cache.

## Teste de ponta a ponta

Com as duas imagens oficiais já disponíveis localmente, executar a partir da
raiz do repositório:

```powershell
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.postgres_collection --output-dir (Join-Path $env:TEMP 'lab05s02-150')
python -m pytest -q LAB5/tests
```

O comando mede um bloco de verificação e registra quatro rodadas em uma
pasta com identificador único. A execução da campanha completa e seu
manifesto fazem parte da issue #151.
