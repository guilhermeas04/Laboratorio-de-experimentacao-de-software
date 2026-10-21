# Sprint 3 — interpretações e limitações

## Base analisada

As análises foram executadas sobre 300 repositórios únicos da amostra final, na janela de 1º de janeiro a 31 de dezembro de 2025. Valores ausentes permanecem ausentes e são excluídos apenas da estatística que depende deles.

## Interpretações por RQ

### RQ01 — frequência de deploy

A frequência mediana foi **0,2493 releases por semana**, com IQR de **0,4027**. A amostra publica, portanto, aproximadamente uma release a cada quatro semanas na mediana. Como a unidade observada é release publicada, o resultado é um proxy de deploy e não mede diretamente produção.

### RQ02 — lead time for changes

O lead time mediano foi **11,6280 dias por release** e **10,7128 dias por commit**. As duas variantes são próximas, o que indica que a escolha do resumo por release ou por commit não altera substancialmente a posição central, embora a dispersão permaneça alta.

### RQ03 — change failure rate

O CFR(a) mediano foi **0,0503** e o CFR(b) mediano foi **0,2903**. A diferença é esperada: CFR(a) observa falhas de CI, enquanto CFR(b) infere releases corretivas por uma heurística. CFR(b) tem um valor ausente entre os 300 repositórios e sua validação manual anterior apresentou F1 de 0,40; por isso não deve ser interpretado como medida direta de falha em produção.

### RQ04 — tempo de recuperação

Entre os casos com episódios recuperados, a mediana foi **0,3953 horas**. A métrica foi calculável para 261 repositórios; 39 não tiveram uma mediana observável. Esses casos não devem ser convertidos em zero: ausência pode representar falta de episódio, ausência de sucesso posterior ou censura no fim da janela.

### RQ05 — associação entre frequência e CFR

Não houve associação estatisticamente significativa entre frequência e CFR(a) (rho = **−0,066**, p = **0,2546**). Houve associação positiva forte entre frequência e CFR(b) (rho = **0,524**, p < **0,0001**). Essa segunda relação deve ser interpretada com cautela, pois a janela de sete dias da heurística CFR(b) depende da cadência de releases e pode produzir associação parcialmente mecânica.

### RQ06 — diferenças entre subgrupos

Após a correção de Holm, 11 dos 24 testes foram significativos. As diferenças mais consistentes apareceram para linguagem, número de contribuidores e idade do repositório, principalmente em lead time e CFR(b). Popularidade por estrelas não apresentou efeito relevante. Os tamanhos de efeito foram em geral pequenos ou médios, então significância estatística não implica diferença operacional grande.

### RQ07 — sensibilidade às definições

Entre as variantes disponíveis, C1×C2 mudou **46,1538%** das classificações (kappa ponderado **0,394997**), C1×C3 mudou **41,5385%** (kappa **0,453220**) e C2×C3 mudou **12,6923%** (kappa **0,828502**). Assim, a classificação é sensível à escolha da variante de lead time e CFR, especialmente quando C1 é comparada a uma variante com CFR(b).

O dataset não contém a variante baseada em tags. Portanto, os resultados atuais de RQ07 não sustentam uma conclusão release-versus-tag; essa ausência deve ser registrada como limitação da coleta.

## Limitações gerais

- Release e workflow run são proxies; o GitHub não informa diretamente deploy em produção nem falha em produção.
- A amostra exige pelo menos cinco releases e 50 runs válidos, restringindo a generalização para projetos populares e ativos.
- CFR(b) depende de heurística e apresentou desempenho limitado na validação manual.
- Recuperação sem episódio observável não é zero e reduz o tamanho efetivo de algumas análises.
- A variante por tags não foi coletada; nenhum valor foi inferido ou simulado.
- Os subgrupos de RQ06 são analisados isoladamente; correlações entre linguagem, idade, estrelas e contribuidores podem confundir as associações.
- O tipo de projeto não foi rotulado para os 300 repositórios.

## Revisão dos artefatos

As tabelas de RQ01–RQ07 estão em seus diretórios de relatório, com contagem de válidos e ausentes. O manifesto de execução está em `sprint3_manifest.json`. As figuras SVG geradas por RQ01–RQ06 permanecem no diretório da respectiva RQ; os arquivos usam os mesmos dados e filtros descritos nas tabelas. A RQ07 fornece tabelas CSV e JSON, sem figura adicional, porque sua saída principal é a matriz de transição e o kappa por par.
