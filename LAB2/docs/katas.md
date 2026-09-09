# Katas de aceitação

O experimento possui exatamente seis katas. Todos usam Python 3.13.7, recebem um
objeto JSON representado por um `dict` e exportam somente `solve(value)`. A
função deve devolver um valor JSON-compatível. Entradas inválidas devem lançar
`ValueError`. A saída de `lab02-katas` é a contagem usada no registro do trial:
`total`, `passing` e `failing`.

Os arquivos em `code/tests/acceptance/` e os casos em
`code/src/lab02/kata_catalog.py` são congelados antes dos trials. Eles são a
mesma fonte para pytest e para o runner. Não há implementação de referência no
repositório: `code/templates/` contém apenas stubs iniciais.

## Catálogo

### K01 - Intervalos consolidados

Entrada: `{"intervals": [[inicio, fim], ...]}`. Retorne os intervalos ordenados,
consolidados quando se sobrepõem ou encostam. Intervalos devem ter inteiros e
`inicio <= fim`; a lista vazia é válida.

Origem e baixa indexação: elaboração própria para o experimento, combinando
normalização de agenda com uma regra explícita de adjacência. Não foi copiado de
uma plataforma de exercícios; a baixa indexação é justificada por busca manual
no catálogo do projeto em 2026-09-08 e pela ausência de identificador ou URL de
origem externa.

### K02 - Primeiro caractere único

Entrada: `{"text": texto}`. Retorne o índice do primeiro caractere que ocorre uma
única vez, ou `-1` se não existir. O índice é baseado em zero e a comparação é
sensível a maiúsculas/minúsculas.

Origem e baixa indexação: elaboração própria, com contrato de índice em vez de
retornar o caractere. O caso é deliberadamente pequeno e não usa o enunciado de
uma coleção pública; a busca manual no repositório não encontrou versão
publicada equivalente.

### K03 - Rotação de matriz quadrada

Entrada: `{"grid": matriz, "turns": k}`. Retorne a matriz quadrada girada 90
graus no sentido horário `k` vezes; valores negativos são permitidos e devem
ser normalizados. Matrizes 1x1 são válidas e toda linha deve ter o mesmo
comprimento. Matriz vazia ou não quadrada é inválida.

Origem e baixa indexação: elaboração própria para manter o mesmo contrato de
entrada/saída dos demais katas, incluindo normalização de rotações negativas.
Não há solução de referência no repositório nem fonte externa vinculada.

### K04 - Troco com menor quantidade de moedas

Entrada: `{"amount": centavos, "coins": [denominacoes]}`. Retorne uma lista de
quantidades na mesma ordem de `coins`, usando o menor número possível de moedas
e somando exatamente `amount`. `amount` é inteiro não negativo, moedas são
inteiras positivas sem repetição; quando não houver combinação, a entrada é
inválida.

Origem e baixa indexação: elaboração própria com saída de vetor de contagens,
em vez do formato mais comum de apenas retornar o número de moedas. A variação
foi criada para este protocolo e não tem referência externa no projeto.

### K05 - Janela livre em agenda

Entrada: `{"busy": [[inicio, fim], ...], "window": [inicio, fim],
"duration": minutos}`. Retorne a primeira janela livre `[inicio, fim]` com a
duração solicitada dentro do período disponível. Intervalos ocupados podem vir
fora de ordem e não se sobrepõem à própria janela; se não houver espaço, a
entrada é inválida.

Origem e baixa indexação: elaboração própria a partir de uma agenda de estudo,
com resultado determinístico e regra de primeira oportunidade. A combinação de
janela limitada, intervalos desordenados e saída do intervalo escolhido foi
criada localmente, sem URL ou gabarito externo.

### K06 - Contagem de picos

Entrada: `{"values": [numeros]}`. Retorne quantos picos existem em posições
internas. Um pico é um grupo contíguo de valores iguais, estritamente maior que
o valor imediatamente anterior e posterior; um grupo conta uma vez. Bordas não
são picos e listas com menos de três elementos retornam zero.

Origem e baixa indexação: elaboração própria para exercitar uma regra de
platô que não aparece nos demais casos. O enunciado e os exemplos foram
produzidos para este estudo, sem reutilizar uma kata identificável de catálogo
público.

## Equivalência e calibração

Os seis katas têm cinco casos cada: três normais/limite e um inválido, além de
um caso de fronteira ou ordenação conforme o domínio. Todos exigem validação de
entrada e uma única função, sem bibliotecas externas. A calibragem é executada
somente com os stubs e soluções sintéticas fora de participantes ou dados
experimentais; seus resultados não são gravados em `data/raw/`.

Para calibrar uma solução local:

```powershell
cd LAB2/code
python -m lab02.kata_runner caminho\para\solucao.py
```

Para executar apenas um conjunto:

```powershell
python -m lab02.kata_runner caminho\para\solucao.py --kata-id kata-03
```

Durante trials, entregue apenas o enunciado e o stub correspondente. Não
entregue o catálogo de expected outputs, o runner ou qualquer solução de
referência.
