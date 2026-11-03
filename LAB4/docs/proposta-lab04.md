# LAB04 — Proposta do laboratório

## 1. Identificação

- Disciplina: Laboratório de Experimentação de Software
- Curso: Engenharia de Software
- Laboratório: 04 — Testes de hipótese por dentro: cenário, simulação e visualização
- Valor: 20 pontos
- Período: 6º período — noite

## 2. Objetivo

Entender como testes de hipótese funcionam e quando escolher um teste em vez de
outro, usando simulação e gráficos em um cenário de Engenharia de Software.

O grupo deverá gerar dados sob condições conhecidas. Assim, será possível saber
quando existe ou não efeito e medir empiricamente erros tipo I e poder, algo que
não é possível fazer apenas com uma amostra real.

## 3. Pergunta e hipóteses

Antes da implementação, o grupo deverá escolher um dos pares do enunciado e
registrar uma pergunta em uma frase. A proposta deve declarar:

- H₀: ausência do efeito ou associação especificada na pergunta;
- H₁: existência do efeito ou associação especificada;
- se o teste será unicaudal ou bicaudal;
- qual teste se espera que tenha melhor desempenho e por quê.

A escolha do par ainda está em aberto. A implementação deverá preservar essa
decisão em um arquivo de configuração e nesta proposta quando ela for definida.

## 4. Dados reais

Será coletada uma amostra pequena, aproximadamente 30 observações por grupo
comparado. O repositório deverá registrar:

- fonte dos dados;
- data e procedimento de coleta;
- critérios de inclusão e exclusão;
- unidade de medida;
- limitações da amostra;
- formato e dicionário das colunas.

Os dados originais ficarão em `data/raw/`. Limpeza e transformações deverão ser
gravadas em `data/interim/`, sem sobrescrever os dados brutos.

## 5. Simulação

Os parâmetros das distribuições simuladas serão escolhidos com base na forma e
nas estatísticas descritivas dos dados reais, incluindo assimetria, dispersão,
mediana ou média, conforme o cenário.

Serão executadas as seguintes perguntas experimentais:

### Q1 — Erro tipo I

Gerar 10.000 conjuntos de dados com H₀ verdadeira, aplicar os dois testes e
calcular a proporção de p-valores menores que 0,05. O resultado esperado é
próximo de 5%.

### Q2 — Poder

Repetir a simulação com efeitos crescentes, usando pelo menos cinco tamanhos de
efeito e incluindo efeito zero. Para cada tamanho, calcular a proporção de
rejeições de H₀.

### Q3 — Violação de pressupostos

Repetir Q1 e Q2 em pelo menos uma condição não ideal, como dados muito
assimétricos, presença de outliers ou amostras pequenas. A escolha deverá ser
justificada conforme o cenário.

## 6. Produtos visuais obrigatórios

| Código | Produto |
|---|---|
| G1 | Histogramas dos dados reais e simulados para cada grupo |
| G2 | Distribuição da estatística sob H₀, região de rejeição e p-valor de exemplo |
| G3 | Erro tipo I dos dois testes, com linha de referência em 5% |
| G4 | Curvas de poder em função do tamanho do efeito |

Todos os gráficos devem possuir título, eixos nomeados com unidade, legenda e
cores consistentes para cada teste.

## 7. Dashboard final

O dashboard será o principal artefato de entrega e deverá explicar-se sozinho.
Cada gráfico será acompanhado de duas a quatro frases com a leitura do
resultado e a conclusão do grupo.

Além dos gráficos, deverá apresentar uma tabela dos dados reais contendo, para
cada teste, estatística, p-valor, tamanho do efeito e conclusão.

## 8. Sprints

### Lab04S01 — 7 pontos

- dados reais;
- cenário e hipóteses;
- gerador de dados simulados;
- aplicação dos dois testes em um conjunto simulado;
- gráficos G1 e G2 no dashboard.

### Lab04S02 — 7 pontos

- simulações de Q1, Q2 e Q3;
- gráficos G3 e G4 no dashboard.

### Entrega final — 6 pontos

- dashboard completo: 3 pontos;
- apresentação oral: 3 pontos.

## 9. Reprodutibilidade e gestão

O código deverá rodar do início ao fim com um único comando documentado no
README e usar uma semente fixa, como `numpy.random.default_rng(42)`.

Cada integrante deverá ser Assignee de pelo menos uma Issue com código
commitado em cada sprint. Os commits devem referenciar a Issue correspondente.
O GitHub Projects deve refletir o andamento real, respeitar o limite de WIP e
manter os cartões atualizados.

## 10. Perguntas para a apresentação

A equipe deverá estar preparada para explicar cenário, hipóteses, coleta,
distribuições, funcionamento dos testes, p-valor, erro tipo I, erro tipo II,
poder, violações de pressupostos, tamanho de efeito, tamanho da amostra e
limitações do estudo.

## 11. Critério de conclusão

O laboratório estará completo quando os resultados simulados forem
reproduzíveis, os quatro gráficos estiverem integrados ao dashboard, a análise
dos dados reais estiver documentada e a recomendação final indicar em que
condições cada teste deve ser usado.

