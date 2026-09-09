# Desenho experimental e contrabalanceamento

## 1. Objetivo GQM

**Goal:** avaliar, no contexto de seis katas Python de dificuldade comparável,
o efeito de usar um assistente de IA durante a implementação, considerando
produtividade, eficácia e qualidade estrutural do código.

**Object:** soluções produzidas pelos participantes para `kata-01` a `kata-06`.

**Viewpoint:** participante e equipe de pesquisa, com análise pareada dentro de
cada participante.

**Context:** três participantes, Python 3.13.7, ambiente comum definido na
#47, cronômetro/coleta da #48, métricas estáticas da #49 e testes de aceitação
da #51.

## 2. Questões e hipóteses

### RQ1 - Produtividade

O uso de IA reduz o tempo para concluir uma kata?

- Métrica primária: `time_to_green_seconds`; trials censurados entram como
  `elapsed_seconds = 2100` e não têm tempo para green.
- `H0_1`: a distribuição pareada das diferenças de tempo entre IA e manual tem
  mediana igual a zero.
- `H1_1`: a mediana pareada da diferença `IA - manual` é menor que zero.

### RQ2 - Eficácia

O uso de IA aumenta a proporção de testes de aceitação que passam?

- Métrica primária: `success_rate`, calculada pelo runner congelado da #51 como
  `100 * tests_passing / tests_total`.
- Métrica secundária: indicador de conclusão sem censura (`censored = false`).
- `H0_2`: a distribuição pareada das diferenças de `success_rate` tem mediana
  igual a zero.
- `H1_2`: a mediana pareada da diferença `IA - manual` em `success_rate` é
  maior que zero.

### RQ3 - Qualidade estrutural

O uso de IA altera a qualidade estrutural do código final?

- Métricas primárias, coletadas pela pipeline da #49: LOC, complexidade
  ciclomática média e máxima, percentual de duplicação e índice de
  manutenibilidade.
- `H0_3`: para cada métrica, a distribuição pareada da diferença IA menos
  manual tem mediana igual a zero.
- `H1_3`: para pelo menos uma métrica estrutural, essa mediana é diferente de
  zero.
- A direção não é presumida: menor complexidade/duplicação/LOC e maior índice
  de manutenibilidade são interpretações de qualidade, não critérios para
  excluir observações.

As hipóteses de RQ1 e RQ2 são direcionais, conforme as perguntas de pesquisa;
RQ3 é bicaudal porque não pressupõe melhora ou piora estrutural. O nível de
significância planejado é `alpha = 0,05`; RQ3 deve reportar as cinco métricas
separadamente e aplicar correção de multiplicidade, como Holm, quando forem
feitos cinco testes confirmatórios.

## 3. Variáveis e unidade experimental

A unidade experimental é um trial de um participante resolvendo uma kata sob um
tratamento. O desenho é crossover within-subject: cada participante resolve
cada uma das seis katas exatamente uma vez, três com IA e três manualmente.

| Papel | Variável | Operacionalização |
|---|---|---|
| Independente | tratamento | `with_ai` ou `manual` |
| Controle | participante | `P01`, `P02`, `P03`; usado como bloco pareado |
| Controle | objeto | `kata-01` a `kata-06`; cada participante vê cada objeto uma vez |
| Controle | ordem | `execution_order` de 1 a 6, definida na tabela versionada |
| Primária RQ1 | produtividade | segundos até todos os testes passarem; 2100 para censura |
| Primária RQ2 | eficácia | percentual de testes de aceitação passando |
| Primárias RQ3 | estrutura | LOC, CC média/máxima, duplicação e MI da #49 |
| Processo | uso de IA | nome, versão e `prompt_count` registrados apenas em `with_ai` |

Os testes de aceitação são os mesmos para os dois tratamentos e permanecem
congelados. A solução final também pode ser analisada pela #49, mas os testes
não são alterados por tratamento.

## 4. Tratamentos e regras operacionais

### Tratamento com IA

- O assistente configurado no protocolo deve ser informado por nome e versão
  no início do trial; ambos são gravados no registro da #48.
- São permitidas perguntas sobre interpretação do enunciado, decomposição do
  problema, linguagem Python, diagnóstico do próprio código e revisão da
  própria solução.
- É proibido pedir ou receber a solução de referência, os expected outputs,
  os arquivos de aceitação congelados ou dados/resultados de outro participante.
- Consultas externas à documentação pública da linguagem e da biblioteca
  padrão são permitidas somente se a mesma possibilidade for oferecida nos dois
  tratamentos; não se usa código de terceiros como solução pronta.
- O participante deve registrar `prompt_count` conforme o protocolo da #48.

### Tratamento manual

- Não é permitido usar assistentes de IA, LLMs, geradores de código ou pedir a
  outra pessoa a solução.
- São permitidos o IDE, o interpretador Python 3.13.7, a biblioteca padrão e a
  documentação pública de Python disponível no ambiente.
- O participante pode consultar o enunciado da própria kata, mas não recebe o
  catálogo interno, expected outputs, runner ou qualquer solução de referência.
- `assistant_name`, `assistant_version` e `prompt_count` ficam nulos.

### Início, execução e fim

1. O pesquisador confirma participante, linha da tabela e tratamento.
2. Antes de exibir o enunciado, executa `lab02-trial start` com o `trial_id`,
   kata, tratamento e ordem.
3. O cronômetro começa nesse instante; consultas e edição fazem parte do
   tempo. O pesquisador não pausa o relógio para dúvidas operacionais.
4. O participante entrega a solução quando considerar a implementação pronta,
   ou quando atingir o limite; os expected outputs congelados não são exibidos.
5. O pesquisador executa os mesmos testes congelados da #51 e chama
   `lab02-trial finish` com `tests_total`, `tests_passing` e, apenas com IA,
   `prompt_count`.
6. O código final é preservado para a análise da #49. Registros em
   `data/raw/` são imutáveis e não são corrigidos manualmente.

## 5. Censura e análise

O time-box é de 35 minutos, ou 2100 segundos. Se todos os testes passarem antes
do limite, registra-se `censored = false` e `time_to_green_seconds` igual ao
tempo decorrido. Se ainda houver falhas ao atingir o limite, registra-se
`censored = true`, `elapsed_seconds = 2100`,
`time_to_green_seconds = null` e pelo menos um teste falhando. Alegar sucesso
após o limite é inválido.

Para cada tratamento e métrica serão reportados tamanho amostral, mediana e
IQR (Q3 - Q1). A comparação principal será o teste de Wilcoxon signed-rank
pareado. Para cada participante, calcula-se primeiro a mediana de seus três
trials com IA e a mediana de seus três trials manuais; essas duas medianas
formam um par. Não existe pareamento do mesmo participante na mesma kata, pois
cada participante resolve cada kata somente uma vez. A
hipótese nula será mantida quando não houver evidência suficiente no nível
`alpha = 0,05`; serão reportados estatística, p-valor e tamanho de efeito, sem
interpretar significância como magnitude. Para RQ1, a análise de tempo deve
explicitar os censurados; não se imputa um tempo para green inexistente.

Com apenas três pares de participantes por métrica, a análise é exploratória e
deve reportar os valores individuais, não apenas o p-valor. Com `n = 3`, o
Wilcoxon exato não consegue atingir `p < 0,05`, mesmo no resultado mais extremo;
por isso, ausência de significância não pode ser interpretada como ausência de
efeito. A tabela de execução não contém resultados de trial e pode ser usada
para reproduzir a alocação.

## 6. Ameaças à validade

### Interna

- Aprendizado entre a primeira e a última kata pode influenciar tempo e
  eficácia; a ordem de katas é rotacionada e a posição deve ser registrada.
- Diferenças individuais e assistência desigual podem confundir o efeito; o
  crossover pareia cada participante consigo mesmo e registra nome/versão do
  assistente.
- Contaminação entre tratamentos é possível; separar sessões, não mostrar
  soluções e registrar desvios no protocolo.
- Falhas de ambiente podem parecer falhas de solução; executar o checklist da
  #50 antes da coleta e preservar os registros operacionais.

### Externa

- Três participantes e seis katas não representam todos os programadores,
  linguagens ou tarefas reais.
- Os resultados generalizam apenas para o ambiente Python e perfil de tarefas
  descritos; repetir com mais participantes e objetos para ampliar a validade.

### De construção

- Tempo para green mede produtividade observada, mas não todo o esforço mental.
- Passar testes mede eficácia perante o contrato, não correção para entradas
  não cobertas.
- Os quatro primeiros objetos usam conceitos algorítmicos conhecidos; um
  assistente ou participante pode reconhecer a família do problema, mesmo que
  os contratos e casos tenham sido escritos localmente.
- LOC, complexidade, duplicação e MI são proxies estruturais, não qualidade
  arquitetural completa; por isso são reportadas juntas e sem um escore único.
- `prompt_count` mede quantidade, não qualidade das consultas.

### De conclusão

- Amostra pequena reduz poder e torna p-valores instáveis; reportar pares,
  medianas, IQR e efeito, sem conclusões fortes.
- Censura concentra valores no limite e pode alterar a ordenação; tratar o
  evento explicitamente e não fingir tempos observados após 2100 segundos.
- Cinco métricas em RQ3 aumentam falsos positivos; aplicar Holm nos testes
  confirmatórios e distinguir exploração de confirmação.
- Código incompleto pode parecer artificialmente menor e menos complexo;
  apresentar RQ3 para todos os trials e, complementarmente, somente para os
  trials com 100% dos testes passando.

## 7. Contrabalanceamento reproduzível

A alocação final está em `data/design/counterbalancing.csv` e é gerada pelo
módulo `lab02.counterbalance`. O script não usa aleatoriedade nem dados de
participantes; suas sequências fixas são auditáveis:

```powershell
cd LAB2/code
python -m lab02.counterbalance --output ../data/design/counterbalancing.csv
python -m lab02.counterbalance --check ../data/design/counterbalancing.csv
```

Cada participante tem seis linhas, três `with_ai`, três `manual` e as seis
katas sem repetição. Os pares de dificuldade planejada K01/K05 (intervalos),
K02/K06 (varredura de sequência) e K03/K04 (transformação/otimização) contêm
um tratamento de cada tipo para todo participante. As três
ordens de kata e as três ordens de tratamento são distintas. Em cada posição
da sequência e em cada kata, uma ou duas das três execuções usam IA, que é o
equilíbrio máximo possível com número ímpar de participantes. O `trial_id` segue
o contrato da #48, por exemplo
`P01-K01-AI` e `P01-K02-MANUAL`.
