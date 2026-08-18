# Validacao RQ03 e RQ04

Base: 1000 repositorios do CSV consolidado.

## Quantidade

- Registros analisados: 1000
- Valores ausentes: 0
- Valores invalidos: 0

## Ausentes

- nenhum campo ausente

## Invalidos

- nenhum valor invalido

## Outliers (IQR)

- Releases: 92
- Dias desde `updatedAt`: 8
- Dias desde `pushedAt`: 194

Maiores outliers de releases:

- langchain-ai/langchain: 1000 releases
- vercel/next.js: 1000 releases
- ggml-org/llama.cpp: 1000 releases
- electron/electron: 1000 releases
- storybookjs/storybook: 1000 releases
- home-assistant/core: 1000 releases
- zed-industries/zed: 1000 releases
- lobehub/lobehub: 1000 releases
- ruvnet/ruflo: 1000 releases
- withastro/astro: 1000 releases

Maiores outliers de `pushedAt`:

- exacity/deeplearningbook-chinese: 2450 dias desde o ultimo push
- GitSquared/edex-ui: 1763 dias desde o ultimo push
- lib-pku/libpku: 1686 dias desde o ultimo push
- adobe/brackets: 1528 dias desde o ultimo push
- floodsung/Deep-Learning-Papers-Reading-Roadmap: 1360 dias desde o ultimo push
- atom/atom: 1323 dias desde o ultimo push
- AFNetworking/AFNetworking: 1308 dias desde o ultimo push
- resume/resume.github.com: 1280 dias desde o ultimo push
- testerSunshine/12306: 1234 dias desde o ultimo push
- prakhar1989/awesome-courses: 1202 dias desde o ultimo push

## Limitacao de `updatedAt`

- Mediana de dias desde `updatedAt`: 0.0
- Repositorios com `updatedAt` no dia da coleta: 992
- Mediana de dias desde `pushedAt`: 1.0
- Repositorios com `pushedAt` no dia da coleta: 438

`updatedAt` muda com atividade do repositorio (issues, PRs, wiki) e quase nao
varia entre projetos populares. `pushedAt` foi incluido para medir a ultima
atualizacao do conteudo.
