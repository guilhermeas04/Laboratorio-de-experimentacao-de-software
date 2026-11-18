# LAB05S01 — Proposta do experimento

## 1. Software e motivação

O objeto do estudo é o PostgreSQL, comparando as versões 15 e 17 em instâncias
executadas localmente. O PostgreSQL é um software real, mantido e usado em
ambientes de produção. As evidências e fontes estão registradas em
[`config/study.json`](../config/study.json).

O estudo local evita medir ou sobrecarregar a infraestrutura de terceiros. As
instâncias serão configuradas de forma equivalente e receberão a mesma carga
de consultas representativas.

## 2. Objetivo e pergunta de pesquisa

**Objetivo GQM:** analisar o tempo de execução e o consumo de recursos de
consultas representativas, com o propósito de comparar o desempenho entre as
versões 15 e 17, do ponto de vista de equipes que mantêm bancos PostgreSQL em
produção, no contexto de execuções repetidas em ambiente local controlado.

**Pergunta:** a versão PostgreSQL 17 apresenta desempenho superior à versão
PostgreSQL 15 em consultas representativas?

As métricas iniciais são latência da consulta, throughput, percentual de CPU e
memória utilizada. A análise deve respeitar as escalas e limitações descritas
no dicionário de dados quando ele for consolidado.

## 3. Classificação nas sete categorias

| Categoria | Classificação | Justificativa |
|---|---|---|
| Natureza | Aplicada, quantitativa | Produz evidência prática para uma decisão de atualização de versão. |
| Objetivos | Descritiva e explicativa | Descreve o desempenho observado e investiga diferenças entre versões. |
| Abordagem | Quantitativa, comparativa | Usa medidas numéricas coletadas sob condições equivalentes. |
| Procedimentos | Experimento controlado de laboratório | O grupo controla versão, ambiente, dados e consultas. |
| Tempo | Transversal | A coleta compara versões em uma janela planejada, sem acompanhar mudança histórica em produção. |
| Controle | Alto controle local, com randomização da ordem quando possível | O ambiente é controlado; a ordem das execuções será alternada para reduzir efeito de aquecimento. |
| Nível de evidência | Evidência experimental inicial | A comparação permite inferir diferenças no ambiente estudado, mas não garante generalização para toda produção. |

## 4. Variáveis e desenho inicial

- **Variável independente:** versão do PostgreSQL (15 ou 17).
- **Variáveis dependentes:** latência, throughput, CPU e memória.
- **Constantes:** hardware, sistema operacional, configuração, dataset,
  consultas, número de repetições e procedimento de limpeza.
- **Unidade experimental:** uma execução de uma consulta em uma instância de
  uma versão do PostgreSQL.
- **Hipótese nula:** não há diferença de desempenho entre as versões.
- **Hipótese alternativa:** existe diferença de desempenho entre as versões;
  a direção esperada é favorável ao PostgreSQL 17.

Antes da coleta completa será executado um piloto para verificar o roteiro,
instrumentação, estabilidade das métricas e tamanho necessário da amostra.

## 5. Protocolo ético e de segurança

O protocolo executável está em [`config/ethics.json`](../config/ethics.json).
O estudo não usa participantes, contas reais ou dados pessoais. Não haverá
requisições a serviços externos nem teste de carga em sistemas de terceiros.
Os dados serão sintéticos ou públicos e os segredos permanecerão fora do
repositório.

## 6. Ameaças iniciais à validade

- **Conclusão:** poucas repetições, ruído do sistema operacional e aquecimento
  do cache podem produzir diferenças instáveis; serão usadas repetições,
  estatística descritiva e registro das condições.
- **Interna:** versões podem receber configurações não equivalentes ou a ordem
  pode favorecer uma delas; a configuração será automatizada e a ordem será
  alternada.
- **Construto:** latência e uso de recursos são apenas aproximações de
  desempenho operacional; o estudo explicitará o que cada métrica representa.
- **Externa:** um ambiente local e consultas escolhidas pelo grupo não
  representam todas as instalações PostgreSQL em produção; a conclusão será
  limitada ao contexto medido.

## 7. Entregas da S01

- Configuração do estudo e evidências em `config/study.json`.
- Protocolo ético em `config/ethics.json`.
- Coleta piloto e validação do ambiente nas issues de instrumentação.
- Plano de análise e limitações revisados antes da coleta completa.
