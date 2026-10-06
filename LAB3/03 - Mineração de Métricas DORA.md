## INFORMAÇÕES SOBRE A AVALIAÇÃO

| LAB03 | Laboratório 03 - 20 pontos |
|---|---|

### INFORMAÇÕES DOCENTE

| CURSO: ENGENHARIA DE SOFTWARE | DISCIPLINA: LABORATÓRIO DE EXPERIMENTAÇÃO DE SOFTWARE | TURNO: NOITE | PERÍODO/SALA: 6º |
|---|---|---|---|

**PROFESSOR(A):** Danilo Maia

---

## Mineração de métricas DORA

### 1. Contexto

As métricas DORA (*DevOps Research and Assessment*) tornaram-se o padrão de mercado para medir o desempenho de entrega de software. Elas foram popularizadas pelo livro *Accelerate* (Forsgren, Humble & Kim, 2018) e são atualizadas anualmente pelo relatório *Accelerate State of DevOps*. As quatro métricas clássicas são:

| Métrica | O que mede (definição DORA) | Dimensão |
|---|---|---|
| **Deployment frequency** | Com que frequência a equipe coloca mudanças em produção | Velocidade (*throughput*) |
| **Lead time for changes** | Quanto tempo uma mudança leva desde o commit até estar em produção | Velocidade (*throughput*) |
| **Change failure rate** | Que proporção dos deploys causa falha em produção e exige intervenção (rollback, *hotfix*) | Estabilidade |
| **Tempo de recuperação** | Quanto tempo leva para se recuperar de um deploy que falhou | Estabilidade |

O tempo de recuperação era chamado de *mean time to restore* (MTTR) e passou a se chamar *failed deployment recovery time* em 2023. Em 2024, o DORA acrescentou uma quinta métrica, a *deployment rework rate* (proporção de deploys não planejados, feitos para corrigir problemas), que aparece aqui como bônus (RQ 08). O histórico dessas mudanças está em [A history of DORA's software delivery metrics](https://dora.dev/insights/dora-metrics-history/).

Neste laboratório, o grupo vai **minerar** essas métricas, ou seja, calculá-las automaticamente a partir dos dados públicos de **repositórios open-source reais** que usam CI/CD com GitHub Actions.

#### O problema central: estamos medindo aproximações

O GitHub **não registra "deploys em produção" nem "falhas em produção"**. Um projeto open-source publica *releases*, roda *workflows* de CI e recebe *commits* — e é a partir disso que vamos **inferir** as métricas DORA. Uma medida indireta como essa se chama **proxy**: "release publicada" é um proxy de "deploy"; "execução de CI que falhou" é um proxy de "falha".

Proxies podem enganar. Uma biblioteca que publica uma release por mês não está "deployando" nada em produção; quem faz isso são os usuários dela. Por isso, além de calcular as métricas, o grupo vai:

1. **validar** seus critérios automáticos comparando-os com o julgamento humano (seção 6, "Validação manual"); e
2. **medir o quanto as conclusões mudam** quando a definição da métrica muda (RQ 07, "análise de sensibilidade").

Ou seja: a pergunta deixa de ser só *"qual é o valor da métrica?"* e passa a ser também *"o quanto podemos confiar nesse valor?"*.

**Leitura recomendada antes de começar (≈ 20 min):**
- [DORA's software delivery metrics: the four keys](https://dora.dev/guides/dora-metrics-four-keys/) — definição oficial das métricas e armadilhas comuns de uso.
- [DORA Quick Check](https://dora.dev/quickcheck/) — questionário curto que mostra como o DORA enquadra uma equipe; útil para entender as faixas de desempenho.

### 2. Visão geral do laboratório

| Entrega | O que o grupo produz | Seção do artigo |
|---|---|---|
| **Lab03S01** | Pipeline de coleta funcionando para 100 repositórios, com testes e CI | Introdução + hipóteses |
| **Lab03S02** | Amostra completa (≥ 300 repositórios), métricas calculadas, validação manual | Metodologia |
| **Lab03S03** | Análise estatística das RQ 01 a RQ 07 | Resultados + Discussão |
| **Entrega final** | Replicação do pipeline de outro grupo + resposta às Issues recebidas | Ameaças à validade + Replicação |

O artigo é escrito **aos poucos**, uma seção por sprint, e não deixado para o final. Os detalhes de pontuação e a divisão sugerida por integrante estão na seção 10.

### 3. Definições operacionais comuns (obrigatórias para toda a turma)

Uma **definição operacional** diz exatamente *como* um conceito será medido. "Lead time" é um conceito; "diferença, em horas, entre `commit.author.date` e `release.published_at`" é uma definição operacional. Todos os grupos devem usar as mesmas regras abaixo, para que os resultados sejam comparáveis entre grupos e para que a replicação cruzada da entrega final seja possível.

- **Janela de observação:** 12 meses, com datas de início e fim fixadas pelo professor na abertura do Lab03S01. Só entram no cálculo releases publicadas e workflow runs criados dentro da janela.
- **Branch:** considere apenas o *default branch* do repositório (o branch principal, geralmente `main` ou `master`; o nome está no campo `default_branch` da API).
- **Deploy (unidade de entrega):** uma **release publicada** no GitHub, ou seja, com `draft = false`. Pré-releases (`prerelease = true`) e tags sem release ficam de fora da definição principal e são usadas como **variantes** na RQ 07.
- **Data de um commit:** use `commit.author.date`, que registra quando a mudança foi escrita. Rebases e *squash merges* podem distorcer essa data; registre isso como ameaça à validade.
- **Execuções de CI consideradas:** apenas workflow runs do default branch disparados por `push` (`event = push`). Execuções agendadas (`schedule`) ou manuais não representam mudanças entregues.
- **O que é falha e o que é sucesso:** o campo `conclusion` de cada workflow run define a classificação:

  | `conclusion` | Tratamento |
  |---|---|
  | `success` | Sucesso |
  | `failure`, `timed_out`, `startup_failure` | Falha |
  | `cancelled`, `skipped`, `neutral`, `action_required`, `stale`, ou vazio (execução em andamento) | **Ignorar** — não entra em nenhum cálculo |

- **Critério mínimo de inclusão:** o repositório precisa ter, dentro da janela, pelo menos **5 releases** e **50 workflow runs** válidos no default branch. Repositórios abaixo disso são descartados e contabilizados no funil de seleção (seção 7).
- **Censura:** às vezes o evento que encerra uma medição não acontece antes do fim da janela, por exemplo uma falha que ainda não foi corrigida. Esse caso **não é descartado**: ele é registrado como **censurado**, e o grupo informa quantos casos censurados houve. Descartá-los faria os repositórios parecerem mais rápidos para se recuperar do que de fato são. Leia mais sobre [censura em estatística](https://en.wikipedia.org/wiki/Censoring_(statistics)).

### 4. Coleta de dados: endpoints e armadilhas

A coleta deve ser feita por script próprio do grupo, usando a [API REST](https://docs.github.com/en/rest) e/ou a [API GraphQL](https://docs.github.com/en/graphql) do GitHub (não é permitido usar bibliotecas prontas de acesso à API do GitHub, como PyGithub). Endpoints úteis:

| Dado | Endpoint (REST) | Cuidado |
|---|---|---|
| Repositórios candidatos | [`GET /search/repositories?q=stars:>1000`](https://docs.github.com/en/rest/search/search#search-repositories) | A busca retorna **no máximo 1.000 resultados por consulta**. Para obter mais candidatos, fatie a busca (ex.: por faixas de estrelas, `stars:1000..2000`, `stars:2000..5000`, …, ou por linguagem). |
| Workflows do repositório | [`GET /repos/{owner}/{repo}/actions/workflows`](https://docs.github.com/en/rest/actions/workflows) | `total_count = 0` indica que o repositório não usa Actions. Descarte-o antes de gastar chamadas com ele. |
| Releases | [`GET /repos/{owner}/{repo}/releases`](https://docs.github.com/en/rest/releases/releases) | Use os campos `draft`, `prerelease`, `published_at` e `tag_name`. |
| Tags (variante da RQ 07) | [`GET /repos/{owner}/{repo}/tags`](https://docs.github.com/en/rest/repos/repos#list-repository-tags) | Tags não trazem data: use a data do commit apontado pela tag. |
| Commits entre duas releases | [`GET /repos/{owner}/{repo}/compare/{base}...{head}`](https://docs.github.com/en/rest/commits/commits#compare-two-commits) | Sem paginação, retorna **no máximo 250 commits**. Use `per_page`/`page` para obter todos. |
| Workflow runs | [`GET /repos/{owner}/{repo}/actions/runs?branch=…&event=push&created=AAAA-MM-DD..AAAA-MM-DD`](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository) | Com filtros, retorna **no máximo 1.000 resultados por consulta**. Em repositórios muito ativos, divida a janela em meses e confira se nenhum mês atingiu o teto. |
| Situação do rate limit | [`GET /rate_limit`](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) | Consultar esse endpoint não consome cota. |

**Rate limit:** com token autenticado, a API REST permite um número limitado de requisições por hora. Os cabeçalhos `X-RateLimit-Remaining` (quantas restam) e `X-RateLimit-Reset` (quando a cota renova, em *epoch*) dizem quando o script deve pausar. Leia [Rate limits for the REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) e [Best practices for using the REST API](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api).

**Paginação:** quase todos os endpoints acima retornam resultados em páginas. Siga o cabeçalho `Link` (`rel="next"`) até o fim. Veja [Using pagination in the REST API](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api).

**Dica:** para contar contribuidores sem baixar a lista inteira, faça `GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true` e leia o número da última página no cabeçalho `Link`.

### 5. Questões de Pesquisa

Cada RQ abaixo traz a **métrica**, **como calculá-la** e, quando ajuda, um **exemplo numérico**. Em todas as RQs, reporte **mediana e IQR** (intervalo interquartil, a faixa entre o 1º e o 3º quartil), e não média e desvio-padrão. Métricas de repositórios de software costumam ter distribuições muito assimétricas, com poucos repositórios extremos, e a média é distorcida por eles ([o que é IQR](https://en.wikipedia.org/wiki/Interquartile_range)).

---

**RQ 01. Qual a frequência de deploys dos repositórios populares que usam CI/CD?**

*Métrica:* deployment frequency, em releases por semana.

*Como calcular:* para cada repositório, divida o número de releases publicadas na janela pelo número de semanas da janela (≈ 52,1).

---

**RQ 02. Qual o tempo entre um commit e seu respectivo deploy?**

*Métrica:* lead time for changes, em **duas variantes obrigatórias**.

*Como calcular:* para cada release R da janela, obtenha os commits incluídos nela comparando-a com a release anterior (`compare/{release anterior}...{R}`). A release anterior pode estar fora da janela; se não existir release anterior (é a primeira release da história do repositório), ignore R no cálculo de lead time.

- **(a) Por release:** o lead time de R é `data de R − data do commit mais antigo incluído em R`. O valor do repositório é a mediana entre suas releases.
- **(b) Por commit:** cada commit incluído em R tem lead time `data de R − data do commit`. O valor do repositório é a mediana de **todos** os commits de **todas** as suas releases.

*Exemplo:* a release `v1.1` foi publicada em 15/03 e inclui três commits, de 02/03, 10/03 e 14/03.
- Variante (a): o lead time de `v1.1` é 15/03 − 02/03 = **13 dias**.
- Variante (b): a release contribui com três valores, 13, 5 e 1 dias, que se somam aos commits das demais releases antes de calcular a mediana.

No artigo, explique por que as duas variantes divergem. Uma pista: um único commit antigo "esquecido" numa release faz a variante (a) explodir, mas pouco afeta a (b).

---

**RQ 03. Qual a taxa de falha das mudanças entregues por esses repositórios?**

*Métrica:* change failure rate (CFR), em **duas variantes obrigatórias**.

- **(a) Proxy de CI:** `nº de workflow runs com falha ÷ (nº de falhas + nº de sucessos)`, usando a tabela de `conclusion` da seção 3. Essa variante mede **falha de pipeline**, que é diferente de falha em produção. Discuta essa diferença.
- **(b) Proxy de entrega:** uma release R é considerada **falha** se for seguida, em até **7 dias**, por uma **release corretiva**. O CFR do repositório é `nº de releases que falharam ÷ nº de releases avaliadas`.
  - *Release corretiva* é aquela cujo objetivo principal é corrigir um defeito recente. O grupo define a heurística automática para identificá-la, por exemplo:
    - a versão muda apenas no número de *patch* do [Versionamento Semântico](https://semver.org/lang/pt-BR/) (`2.3.0 → 2.3.1`); e/ou
    - há commits com `revert`, `hotfix` ou `fix` na mensagem entre as duas releases.
  - Essa heurística **precisa** ser validada contra a amostra rotulada manualmente (seção 6).
  - Releases publicadas nos **últimos 7 dias da janela** não podem ser avaliadas, pois ainda não se sabe se haverá correção. Elas ficam fora do denominador (censura).

*Exemplo:*
- `v2.3.0` (10/05) é seguida por `v2.3.1` (12/05), que só muda o *patch* e contém o commit `fix: crash ao abrir arquivo`. Logo, `v2.3.0` **falhou**.
- `v2.4.0` (01/06) é seguida por `v2.5.0` (20/06). Logo, `v2.4.0` **não falhou**.

---

**RQ 04. Qual o tempo de recuperação após uma execução de CI/CD com falha?**

*Métrica:* tempo de recuperação, em horas.

*Como calcular:* ordene cronologicamente as execuções de **um mesmo workflow** no default branch. Um **episódio de falha** começa na primeira falha após um sucesso e termina na próxima execução bem-sucedida desse mesmo workflow. O tempo de recuperação do episódio é `fim da execução bem-sucedida (updated_at) − início da primeira falha (run_started_at)`. O valor do repositório é a mediana de todos os episódios de todos os seus workflows.

*Exemplo* (workflow `CI`, branch `main`):

| Horário | `conclusion` |
|---|---|
| 09:00 | success |
| 10:00 | failure ← início do episódio |
| 10:30 | failure (mesmo episódio) |
| 11:15 | success ← fim do episódio (terminou às 11:20) |

O tempo de recuperação desse episódio é 11:20 − 10:00 = **1h20**. Um episódio que nunca termina dentro da janela é **censurado**: reporte a proporção de episódios censurados por repositório.

---

**RQ 05. Repositórios com maior frequência de deploy apresentam maior ou menor taxa de falha?**

*Métrica:* [correlação de Spearman](https://pt.wikipedia.org/wiki/Coeficiente_de_correla%C3%A7%C3%A3o_de_postos_de_Spearman) (ρ) entre deployment frequency (RQ 01) e CFR (RQ 03), calculada separadamente para as variantes (a) e (b).

*Por que Spearman:* ela não exige que os dados sigam distribuição normal nem que a relação seja linear. Ela mede se "quanto mais X, mais (ou menos) Y" a partir da **ordem** (*ranking*) dos valores. ρ vai de −1 (relação inversa perfeita) a +1 (relação direta perfeita); valores próximos de 0 indicam ausência de relação monotônica. Use [`scipy.stats.spearmanr`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html) e reporte ρ, p-valor e n.

*O que discutir:* o DORA afirma que velocidade e estabilidade **não** são um *trade-off* e que as equipes de melhor desempenho vão bem nas duas dimensões. Os dados open-source confirmam ou contradizem essa afirmação? Lembre-se de que **correlação não implica causalidade**. Inclua um gráfico de dispersão, com eixo em escala logarítmica se os valores variarem muito.

---

**RQ 06. Quais características dos repositórios estão associadas a um melhor desempenho DORA?**

*Métrica:* comparação das métricas DORA (RQ 01 a 04) entre subgrupos de repositórios.

*Passo a passo:*
1. Escolha **no mínimo três fatores** entre: linguagem principal, popularidade (quartis de estrelas), nº de contribuidores (quartis), idade do repositório (quartis) e **tipo do projeto** (biblioteca/framework × aplicação/serviço × ferramenta CLI, rotulado manualmente na seção 6). Fatores numéricos são convertidos em grupos pelos quartis.
2. Para cada combinação de fator × métrica, aplique o teste de [Kruskal-Wallis](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.kruskal.html). Ele responde: "as distribuições da métrica diferem entre os grupos?". Se o fator tiver só dois grupos, use [Mann-Whitney](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html).
3. **Corrija os p-valores para comparações múltiplas.** Com três fatores e quatro métricas, são pelo menos 12 testes. Com tantos testes ao nível de 5%, é provável que algum dê "significativo" por puro acaso. Use a correção de [Holm](https://en.wikipedia.org/wiki/Holm%E2%80%93Bonferroni_method) via [`statsmodels…multipletests`](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) com `method='holm'`.
4. **Reporte o tamanho de efeito**, porque um p-valor pequeno diz que a diferença existe, mas não se ela é grande:
   - Kruskal-Wallis: **ε² = H / (n − 1)**, em que H é a estatística do teste e n o total de repositórios. Varia de 0 a 1.
   - Comparação entre dois grupos: **Cliff's delta**, δ = 2·U₁ / (n₁·n₂) − 1, em que U₁ é a estatística retornada por `mannwhitneyu(x, y)`. Varia de −1 a +1. Interpretação usual (Romano et al., 2006): |δ| < 0,147 desprezível; < 0,33 pequeno; < 0,474 médio; ≥ 0,474 grande.

---

**RQ 07. O quanto a classificação DORA de um repositório depende da definição operacional escolhida?** *(análise de sensibilidade)*

*Métrica:* proporção de repositórios que mudam de categoria DORA entre definições, e concordância entre as classificações.

*Passo a passo:*
1. Monte **pelo menos três combinações** de definições operacionais. Exemplo:

   | Combinação | Unidade de deploy | Lead time | CFR |
   |---|---|---|---|
   | C1 (referência) | release | (a) | (a) |
   | C2 | release + pré-release | (b) | (b) |
   | C3 | tag | (b) | (a) |

2. Para cada combinação, classifique cada repositório em Elite / High / Medium / Low usando a tabela de referência abaixo.
3. Para cada par de combinações (C1×C2, C1×C3, C2×C3), calcule:
   - a **% de repositórios que mudaram de categoria**; e
   - o **kappa de Cohen ponderado**, com [`cohen_kappa_score(..., weights='linear')`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html). A ponderação faz uma troca Elite→High pesar menos que uma troca Elite→Low, porque as categorias são ordenadas.
4. Discuta: as conclusões das RQ 01 a 06 são **robustas**, ou dependem de uma escolha arbitrária de definição?

*Tabela de referência para a classificação DORA nesta disciplina.* Os relatórios DORA definem as faixas de desempenho por análise de agrupamento (*clusters*) das respostas de cada ano, e as faixas mudam de edição para edição. Para que toda a turma classifique da mesma forma, usamos os cortes fixos abaixo, **adaptados** dessas faixas:

| Métrica | Elite | High | Medium | Low |
|---|---|---|---|---|
| Deployment frequency | ≥ 7 por semana (≈ diária ou mais) | ≥ 1 e < 7 por semana | ≥ 1 por mês e < 1 por semana | < 1 por mês |
| Lead time (mediana) | < 1 dia | 1 dia a < 1 semana | 1 semana a < 30 dias | ≥ 30 dias |
| Change failure rate | ≤ 15% | > 15% e ≤ 30% | > 30% e ≤ 45% | > 45% |
| Tempo de recuperação (mediana) | < 1 hora | 1 hora a < 1 dia | 1 dia a < 1 semana | ≥ 1 semana |

**Classificação geral do repositório:** atribua 4 pontos a Elite, 3 a High, 2 a Medium e 1 a Low em cada uma das quatro métricas. A categoria geral é a **mediana** desses quatro valores, **arredondada para baixo**. Exemplo: com as notas (4, 3, 3, 1), a mediana é 3, logo o repositório é **High**.

---

**RQ 08 (bônus, +1 ponto).** Escolha **uma** das opções:
- **Rework rate:** calcule a proporção de releases corretivas (definidas na RQ 03 b) sobre o total de releases. Essa é a métrica que o DORA adicionou em 2024 ([definição](https://dora.dev/guides/dora-metrics-four-keys/)). Discuta em que ela difere do CFR (b).
- **Evolução temporal:** calcule as métricas DORA por trimestre dentro da janela e verifique, repositório a repositório, se há tendência de melhora ou piora com o teste de Mann-Kendall (biblioteca [`pymannkendall`](https://pypi.org/project/pymannkendall/)). Reporte a proporção de repositórios com tendência significativa em cada direção.

### 6. Validação manual (amostra-ouro)

Uma heurística automática (como "release que só muda o *patch* é corretiva") pode errar bastante. A forma de saber o quanto ela erra é compará-la com o julgamento de pessoas. O conjunto rotulado por humanos e usado como referência se chama **amostra-ouro** (*gold standard*). Na Sprint 02, o grupo deve:

1. **Sortear 60 repositórios** da amostra final, com semente fixa e documentada no código, por exemplo `df.sample(n=60, random_state=42)`, para que o sorteio seja reproduzível.
2. **Rotular de forma independente.** Cada um dos três integrantes, **sem consultar os demais e sem ver a saída da heurística**, preenche sua própria planilha com:
   - (i) o **tipo do projeto**: biblioteca/framework, aplicação/serviço, ferramenta CLI ou outro;
   - (ii) se as releases do repositório **representam entregas reais ao usuário**: sim, não ou incerto;
   - (iii) para **5 releases sorteadas** de cada repositório, se a release é **corretiva** (sim/não), lendo as *release notes* e a lista de commits.

   *Dica:* gere a planilha automaticamente com uma coluna de links diretos para a página da release no GitHub. Isso economiza muito tempo.
3. **Calcular a concordância entre os três avaliadores** com o **kappa de Fleiss**, em cada uma das três dimensões. Em Python, use [`aggregate_raters`](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.aggregate_raters.html) seguido de [`fleiss_kappa`](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.fleiss_kappa.html) do statsmodels.
   - O kappa corrige a concordância que aconteceria **por acaso**. Por isso ele é mais honesto que a simples "% de vezes em que concordamos" ([explicação](https://en.wikipedia.org/wiki/Fleiss%27_kappa)).
   - Interpretação usual (Landis & Koch, 1977): < 0 pobre; 0–0,20 leve; 0,21–0,40 razoável; 0,41–0,60 moderada; 0,61–0,80 substancial; 0,81–1 quase perfeita.
   - Um kappa baixo indica que o próprio critério é ambíguo. Isso é um achado, e deve ser discutido no artigo.
4. **Chegar a um consenso.** Os três discutem os casos divergentes e definem o **rótulo de consenso**. Registre no repositório o protocolo de desempate usado (ex.: maioria simples; casos 1-1-1 decididos em reunião).
5. **Avaliar a heurística automática** de release corretiva frente ao consenso, calculando [precisão, recall e F1](https://en.wikipedia.org/wiki/Precision_and_recall) com [`precision_recall_fscore_support`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html):
   - **Precisão:** das releases que a heurística marcou como corretivas, quantas realmente eram?
   - **Recall:** das releases realmente corretivas, quantas a heurística encontrou?
   - **F1:** média harmônica das duas, `2·P·R / (P + R)`.

   *Exemplo:* a heurística marcou 40 releases como corretivas, e o consenso confirma 30 delas, então a precisão é 30/40 = 75%. O consenso identificou 50 corretivas no total, e a heurística acertou 30, então o recall é 30/50 = 60%. O F1 fica em ≈ 0,67.

   Se o F1 ficar abaixo de 0,70, refine a heurística e reavalie. Documente no artigo cada versão testada e o F1 obtido por ela.

O **tipo do projeto** rotulado aqui é usado na RQ 06. A **validação da heurística** sustenta a RQ 03 (b) e a seção de ameaças à validade.

### 7. Requisitos de engenharia do pipeline

A coleta deixa de ser "um script que roda uma vez no meu computador" e passa a ser um **pipeline reprodutível**. Na entrega final, **outro grupo** vai executá-lo seguindo apenas o README. Requisitos:

- **Execução com um único comando**, a partir do README (ex.: `python -m pipeline --config config.yaml`). O token do GitHub é lido de uma variável de ambiente (ex.: `GITHUB_TOKEN`) e **nunca** commitado no repositório.
- **Cache local e retomada.** Cada resposta da API é salva em disco (ex.: um JSON por repositório e endpoint, ou um banco SQLite). Se a coleta for interrompida por rate limit, queda de rede ou `Ctrl+C`, rodar o comando de novo **continua de onde parou**, sem repetir chamadas já feitas. Isso economiza horas de coleta e de cota da API.
- **Tratamento de rate limit e erros.** O script lê `X-RateLimit-Remaining`/`X-RateLimit-Reset` e espera automaticamente quando a cota acaba. Erros temporários (respostas 5xx) são repetidos com [*backoff* exponencial](https://en.wikipedia.org/wiki/Exponential_backoff): espera 1 s, depois 2 s, 4 s, 8 s…, até um limite de tentativas.
- **Testes automatizados** das funções que calculam as métricas (lead time, CFR, tempo de recuperação e classificação DORA), com [pytest](https://docs.pytest.org/en/stable/).
  - Use [*fixtures*](https://docs.pytest.org/en/stable/explanation/fixtures.html): pequenos dados de entrada construídos à mão, cujo resultado correto o grupo já sabe calcular no papel. Os exemplos numéricos da seção 5 são bons pontos de partida.
  - Inclua **casos de borda**: release sem commits novos, falha nunca recuperada (censurada), repositório com uma única release e execuções `cancelled` (que devem ser ignoradas).
  - Cobertura mínima de **80% do módulo de métricas**, medida com [pytest-cov](https://pytest-cov.readthedocs.io/) (`pytest --cov=metricas --cov-report=term-missing`).
- **CI do próprio grupo.** Os testes rodam no GitHub Actions do repositório do grupo a cada push ([guia: Building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)). De quebra, o grupo passa a gerar os mesmos dados de CI que está minerando. Um ponto de partida mínimo (`.github/workflows/testes.yml`):

  ```yaml
  name: testes
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.12"
        - run: pip install -r requirements.txt
        - run: pytest --cov=metricas --cov-fail-under=80
  ```

- **Funil de seleção.** O pipeline gera automaticamente uma tabela com quantos repositórios restaram em cada etapa e por que os demais foram descartados. Exemplo: 4.000 candidatos → 2.900 com Actions → 610 com ≥ 5 releases e ≥ 50 runs → 350 na amostra final. Essa tabela vai para a seção de Metodologia do artigo.
- **Dicionário de dados.** Cada coluna dos CSVs finais é documentada com nome, tipo, unidade (horas? dias? %?) e fórmula ou origem na API. Sem isso, o grupo replicador não consegue comparar os resultados.

### 8. Relatório Final (artigo)

O relatório tem formato de **artigo científico**, no [template da SBC (Overleaf)](https://www.overleaf.com/latex/templates/sbc-conferences-template/blbxwjwzdngr), com no máximo 10 páginas. Ele é a base do artigo atualizado no Lab04 e é **escrito aos poucos**: cada sprint entrega uma seção revisada (seção 10). Estrutura:

1. **Introdução**, com uma hipótese informal por RQ (o que o grupo *espera* encontrar e por quê), escrita **antes** de ver os dados.
2. **Metodologia:** fonte de dados, funil de seleção, janela, definições operacionais e suas variantes, e protocolo de validação manual.
3. **Resultados por RQ**, com mediana, IQR e classificação DORA, em tabelas e gráficos.
4. **Discussão:** hipóteses vs. resultados. O que surpreendeu? Por quê?
5. **Ameaças à validade**, nas quatro categorias clássicas (Wohlin et al., *Experimentation in Software Engineering*), cada uma apoiada nos resultados da validação manual e da análise de sensibilidade:
   - *de construto:* estamos medindo o que achamos que medimos? (ex.: release ≠ deploy)
   - *interna:* há fatores não controlados que explicam os resultados? (ex.: repositórios mais antigos têm mais releases)
   - *externa:* os resultados valem para além da amostra? (ex.: projetos populares ≠ projetos corporativos)
   - *de conclusão:* a análise estatística é adequada? (ex.: muitas comparações, amostras pequenas em alguns subgrupos)
6. **Replicação cruzada:** o relato da seção 9.
7. Link do repositório/GitHub Projects do grupo.

Link do repositório/GitHub Projects: `<preencher>`

### 9. Replicação cruzada (entrega final)

Um resultado científico só é confiável se outra pessoa conseguir reproduzi-lo. Na entrega final, o professor sorteia para cada grupo o pipeline de **outro grupo** da turma. O grupo **replicador** deve:

1. **Executar** o pipeline do outro grupo **usando apenas o README**, sobre uma subamostra de 30 repositórios do dataset original, sem pedir ajuda ao grupo autor. Se travar, isso é um resultado a ser registrado.
2. **Comparar** os valores obtidos com os do CSV original: diferença relativa por métrica e % de repositórios com a mesma classificação DORA. Pequenas diferenças são esperadas, porque os repositórios continuam recebendo commits e as datas de coleta diferem; explique-as.
3. **Abrir Issues no repositório do grupo autor** relatando cada problema (falha de execução, documentação faltante, divergência de resultado), com evidências: comando executado, mensagem de erro, valores esperados e obtidos.
4. **Registrar** o resultado na seção "Replicação cruzada" do próprio artigo: o estudo foi reproduzível? O que impediu ou dificultou?

O grupo **autor**, por sua vez, deve responder a cada Issue recebida até o prazo final, corrigindo o pipeline ou justificando por que não corrigiu. Essas Issues devem ser adicionadas ao seu próprio GitHub Projects.

### 10. Processo de Desenvolvimento

**Contribuição individual por sprint.** Em toda sprint (S01, S02, S03 e entrega final), cada integrante do trio deve ser Assignee de ao menos uma Issue com artefato de código commitado (script, teste, notebook ou análise), e não apenas de Issues de escrita. A ausência de commits atribuíveis a um integrante em uma sprint zera a parcela individual daquele integrante na sprint.

**Lab03S01** (5 pontos):
- Pipeline de coleta base funcionando para **100 repositórios**, com:
  - seleção e funil registrado;
  - releases, commits entre releases e workflow runs do default branch na janela;
  - cache/retomada e tratamento de rate limit.
- Testes unitários das funções de cálculo, com *fixtures*, e CI do grupo rodando os testes.
- Artigo: **introdução com hipóteses informais** para cada RQ.

*Divisão sugerida por integrante:*
- **A:** seleção de repositórios, funil e coleta de metadados (estrelas, linguagem, contribuidores, idade).
- **B:** coleta de releases/tags e de commits entre releases, mais as funções e testes de lead time.
- **C:** coleta de workflow runs (com subdivisão mensal da janela), camada de cache/rate limit, e as funções e testes de CFR (a) e tempo de recuperação.

Cada componente é uma Issue própria, testável isoladamente antes de ser integrada ao pipeline único do grupo.

**Lab03S02** (5 pontos):
- Amostra final completa, definida pelo grupo, com **mínimo de 300 repositórios após os filtros**.
- Métricas calculadas em todas as variantes obrigatórias.
- Dataset em .csv com dicionário de dados.
- **Validação manual:** amostra-ouro de 60 repositórios, kappa de Fleiss, e precisão/recall/F1 da heurística corretiva.
- Artigo: **seção de metodologia** completa.

*Divisão sugerida por integrante:* os três rotulam a amostra-ouro de forma independente, cada um com sua Issue e seu arquivo de rótulos commitado. Além disso:
- **A:** cálculo de concordância e consolidação do consenso.
- **B:** implementação e refinamento da heurística de release corretiva (CFR b) a partir da validação.
- **C:** coleta completa, consolidação do dataset e dicionário de dados.

**Lab03S03** (5 pontos):
- Análise completa das RQ 01 a RQ 07:
  - estatística descritiva (mediana e IQR) e classificação DORA;
  - correlações (RQ 05);
  - testes com tamanho de efeito e correção para comparações múltiplas (RQ 06);
  - análise de sensibilidade (RQ 07).
- Artigo: **seções de resultados e discussão**.

*Divisão sugerida por integrante:*
- **A:** RQ 01 a RQ 04 e a classificação DORA de referência (C1).
- **B:** RQ 05 e RQ 06.
- **C:** análise de sensibilidade (RQ 07) e, se o grupo optar, o bônus (RQ 08).

Cada análise é um notebook ou script próprio, reexecutável a partir do CSV.

**Entrega final** (5 pontos):
- Replicação cruzada (2 pontos).
- Resposta às Issues recebidas do grupo replicador (1 ponto).
- Artigo completo e revisado, incluindo **ameaças à validade** e **relato da replicação** (2 pontos).

*Divisão sugerida por integrante:*
- **A:** executa o pipeline do outro grupo e registra os problemas de execução.
- **B:** compara os resultados com o CSV original e abre as Issues de divergência.
- **C:** trata as Issues recebidas do grupo replicador no próprio pipeline.

A seção de ameaças à validade e a revisão final do artigo são feitas pelos três.

**Prazo final:** conforme cronograma da disciplina.
**Valor total:** 20 pontos (+1 de bônus pela RQ 08) | Desconto de até 10% da nota da sprint por qualidade insuficiente do uso do GitHub Projects (WIP não respeitado, Issues sem Assignee, cartões desatualizados, ausência de evolução semanal).
**Observação:** não é permitido o uso de bibliotecas de terceiros que realizem consultas à API do GitHub. A coleta deve ser feita por script próprio do grupo, via GraphQL e/ou REST. Bibliotecas de análise de dados e estatística (ex.: pandas, SciPy, statsmodels, scikit-learn, pymannkendall) são permitidas. A correção é feita a partir do GitHub Projects: commits sem referência ao número da Issue correspondente não serão considerados.

### 11. Perguntas frequentes

**O repositório usa tags, mas não publica releases. Entra na amostra?**
Não na definição principal, que exige ≥ 5 releases. Ele é descartado e contabilizado no funil. As tags só aparecem como variante na RQ 07.

**O `compare` entre duas releases retornou erro 404.**
Isso costuma acontecer quando a tag foi apagada ou reescrita. Registre o caso, ignore aquela release no cálculo de lead time e conte quantas releases foram ignoradas por esse motivo.

**Um repositório tem dezenas de workflows (lint, docs, testes, release…). Uso todos?**
Sim, mas sempre agrupando por workflow. O CFR (a) considera todos os workflows juntos; o tempo de recuperação (RQ 04) é calculado **dentro** de cada workflow e só depois agregado pela mediana.

**A coleta de 300+ repositórios vai estourar o rate limit?**
Provavelmente, várias vezes, e é exatamente por isso que cache e retomada são requisitos. Comece cedo e deixe a coleta rodando em segundo plano. Teste sempre com poucos repositórios antes de rodar a amostra completa.

**Podemos usar outra linguagem além de Python?**
Sim, desde que o pipeline continue executável por outro grupo com um único comando documentado no README, e que exista equivalente para os testes com cobertura.

### 12. Glossário e materiais de apoio

| Termo | Significado curto | Para saber mais |
|---|---|---|
| Proxy | Medida indireta usada no lugar de uma que não se pode observar | Seção 1 |
| Definição operacional | Regra exata de como um conceito é medido | Seção 3 |
| Default branch | Branch principal do repositório (`main`, `master`…) | [GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/changing-the-default-branch) |
| Release / pré-release / draft | Versão publicada / versão marcada como instável / rascunho não publicado | [Releases API](https://docs.github.com/en/rest/releases/releases) |
| SemVer | Versionamento `MAJOR.MINOR.PATCH` | [semver.org](https://semver.org/lang/pt-BR/) |
| Censura | Observação cujo evento final não ocorreu dentro da janela | [Wikipedia](https://en.wikipedia.org/wiki/Censoring_(statistics)) |
| Mediana / IQR | Valor central / faixa entre o 1º e o 3º quartil | [Wikipedia](https://en.wikipedia.org/wiki/Interquartile_range) |
| Amostra-ouro | Subconjunto rotulado por humanos usado como referência | Seção 6 |
| Kappa (Cohen / Fleiss) | Concordância entre avaliadores, corrigida pelo acaso | [Wikipedia](https://en.wikipedia.org/wiki/Fleiss%27_kappa) |
| Precisão / Recall / F1 | Qualidade de um classificador frente a uma referência | [Wikipedia](https://en.wikipedia.org/wiki/Precision_and_recall) |
| Spearman | Correlação baseada na ordem dos valores | [Wikipedia](https://pt.wikipedia.org/wiki/Coeficiente_de_correla%C3%A7%C3%A3o_de_postos_de_Spearman) |
| Kruskal-Wallis / Mann-Whitney | Testes não paramétricos de diferença entre grupos | [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.kruskal.html) |
| Tamanho de efeito | *Quão grande* é a diferença, além de ela existir | RQ 06 |
| Correção de Holm | Ajuste de p-valores quando se fazem muitos testes | [Wikipedia](https://en.wikipedia.org/wiki/Holm%E2%80%93Bonferroni_method) |
| Fixture | Dado de teste preparado para um caso conhecido | [pytest](https://docs.pytest.org/en/stable/explanation/fixtures.html) |
| Backoff exponencial | Repetir uma requisição com esperas crescentes | [Wikipedia](https://en.wikipedia.org/wiki/Exponential_backoff) |

**Referências principais:**
- Forsgren, N.; Humble, J.; Kim, G. *Accelerate: The Science of Lean Software and DevOps*. IT Revolution, 2018.
- DORA. [Relatórios *Accelerate State of DevOps*](https://dora.dev/research/) e [guia das métricas](https://dora.dev/guides/dora-metrics-four-keys/).
- Wohlin, C. et al. *Experimentation in Software Engineering*. Springer, 2012 (capítulo sobre ameaças à validade).
- Romano, J. et al. *Appropriate statistics for ordinal level data*. 2006 (interpretação do Cliff's delta).
- Landis, J. R.; Koch, G. G. *The measurement of observer agreement for categorical data*. Biometrics, 1977.
