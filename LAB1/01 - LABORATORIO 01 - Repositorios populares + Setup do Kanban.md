## INFORMAÇÕES SOBRE A AVALIAÇÃO

| LAB01 | Laboratório 01 - 15 pontos |
|---|---|

### INFORMAÇÕES DOCENTE     

| CURSO: ENGENHARIA DE SOFTWARE | DISCIPLINA: LABORATÓRIO DE EXPERIMENTAÇÃO DE SOFTWARE | TURNO: NOITE | PERÍODO/SALA: 6º |
|---|---|---|---|

**PROFESSOR(A):** Danilo Maia

---

## Características de repositórios populares + Setup do Kanban

Neste laboratório, vamos estudar as principais características de sistemas populares open-source, dando início também ao uso do quadro Kanban que acompanhará o grupo durante todo o semestre. Para a parte de mineração, colete os dados indicados a seguir para os 1.000 repositórios com maior número de estrelas no GitHub e discuta os valores obtidos.

### Parte 1 — Questões de Pesquisa

**RQ 01.** Sistemas populares são maduros/antigos?
Métrica: idade do repositório (calculado a partir da data de sua criação)

**RQ 02.** Sistemas populares recebem muita contribuição externa?
Métrica: total de pull requests aceitas

**RQ 03.** Sistemas populares lançam releases com frequência?
Métrica: total de releases

**RQ 04.** Sistemas populares são atualizados com frequência?
Métrica: tempo até a última atualização

**RQ 05.** Sistemas populares são escritos nas linguagens mais populares?
Métrica: linguagem primária de cada repositório
*(defina e referencie explicitamente a fonte usada para "linguagens mais populares" — ex.: TIOBE Index, GitHut ou o Octoverse do GitHub — mantendo a mesma referência ao longo de todo o laboratório)*

**RQ 06.** Sistemas populares possuem um alto percentual de issues fechadas?
Métrica: razão entre issues fechadas e total de issues

**RQ 07:** Sistemas escritos em linguagens mais populares recebem mais contribuição externa, lançam mais releases e são atualizados com mais frequência? (divida os resultados das RQs 02, 03 e 04 por linguagem)

### Parte 2 — Setup do GitHub Projects do grupo

O grupo (trio) deve constituir, a partir deste laboratório, o GitHub Projects (v2) que será usado até o final do semestre. Defina e documente:

1. **Crie um GitHub Projects (v2)** vinculado ao repositório do grupo.
2. **Cartões = Issues** do repositório, adicionadas ao Project (não usar "draft issues" soltas — cada tarefa deve virar uma Issue de verdade, rastreável pela API) e **atribuídas a um responsável** (campo Assignee).
3. **Colunas do board** (campo Status): no mínimo `Backlog → To Do → Doing → Review → Done`.
4. **Limite de WIP** (Work in Progress) para a coluna Doing — defina e justifique o número escolhido.
5. Todas as tarefas do próprio Lab01 (e dos laboratórios seguintes) devem ser quebradas em Issues e movimentadas no board conforme o progresso real do grupo, não retroativamente.
6. **Snapshot de fechamento de sprint:** ao final de cada sprint (Lab01S01, S02, S03...), rode um script GraphQL (reaproveitando o que já foi feito na Parte 1) que exporte os itens do Project e seu status atual para um arquivo CSV. Esses snapshots, acumulados sprint a sprint, serão a base de dados dos Labs 04 e 05 — como o GitHub Projects não guarda histórico de mudanças de coluna consultável via API, essa série de snapshots faz esse papel.
7. **Referencie o número da Issue em cada commit** (ex.: `#12 implementa consulta GraphQL`), para que o GitHub vincule automaticamente commit ↔ Issue no histórico. **A correção do professor é feita a partir do board**: commits sem essa referência não serão considerados na avaliação, mesmo que estejam no repositório.

### Relatório Final

Documento com: (i) introdução com hipóteses informais sobre as RQs; (ii) metodologia de coleta; (iii) resultados por RQ (valores medianos, contagem por categoria quando aplicável); (iv) discussão hipótese vs. resultado; (v) uma seção "Configuração do processo", descrevendo a estrutura do GitHub Projects (colunas, política de WIP) e um print do board ao final do laboratório, com o link do repositório/GitHub Projects do grupo.

Link do repositório/GitHub Projects: `<preencher>`

### Processo de Desenvolvimento

**Lab01S01** (4 pontos): Consulta GraphQL para 100 repositórios (todos os dados/métricas necessários) + requisição automática + GitHub Projects criado, com colunas (Status) e limite de WIP definidos e primeiras Issues em uso.

*Divisão sugerida por integrante (desde esta sprint, para viabilizar desenvolvimento individual semanal em um trio):* distribua as RQs em 3 partes, uma por integrante (ex.: A → RQ01+RQ02; B → RQ03+RQ04; C → RQ05+RQ06+bônus). Cada integrante implementa e testa, em Issue própria, a extração e uma validação rápida (numa amostra de 5-10 repositórios) dos campos/métricas da sua parte, antes de integrar ao script único de consulta do grupo.

**Lab01S02** (4 pontos): Paginação (consulta 1000 repositórios) + dados em .csv + primeira versão do relatório com hipóteses informais + board atualizado e primeiro snapshot exportado, refletindo o fluxo real de trabalho do grupo em S01 e S02.

*Divisão sugerida por integrante:* a paginação em si (tarefa mecânica) pode ficar com qualquer integrante, mas cada integrante deve validar individualmente, para a sua parte de RQs, a consistência dos dados nos 1000 repositórios (distribuição, outliers, valores ausentes) e escrever, em Issue própria, a hipótese informal correspondente.

**Lab01S03** (4 pontos): Análise e visualização de dados para as 7 RQs.

**Relatório Final** (3 pontos): elaboração do documento final (ver seção "Relatório Final" acima), incluindo o anexo com print do board mostrando o fluxo completo do Lab01 e a política de WIP em uso.

**Prazo final:** conforme cronograma da disciplina.
**Valor total:** 15 pontos | Desconto de 1,0 ponto por dia de atraso | Desconto de até 10% da nota da sprint por qualidade insuficiente do uso do GitHub Projects (WIP não respeitado, Issues sem Assignee, cartões desatualizados, ausência de evolução semanal).
**Observação:** não é permitido o uso de bibliotecas de terceiros que consultem a API do GitHub — a query GraphQL deve ser escrita e consumida por script próprio do grupo. A correção é feita a partir do GitHub Projects: commits sem referência ao número da Issue correspondente não serão considerados.
