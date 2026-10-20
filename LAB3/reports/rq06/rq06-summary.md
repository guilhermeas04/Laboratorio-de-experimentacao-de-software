# RQ06 - Métricas DORA por subgrupo

Repositórios: **300**. Fatores: Linguagem principal, Popularidade (quartis de estrelas), Contribuidores (quartis), Idade do repositorio (quartis).
Testes: 24 (4 fatores x 6 métricas). Correção de Holm sobre a família inteira.

## Hipóteses

H0 de cada teste: a distribuição da métrica é igual em todos os grupos do fator. H1: ao menos um grupo difere.

- **Linguagem principal:** A distribuicao de cada metrica difere entre linguagens. Ecossistemas tem cadencias de release e praticas de CI diferentes.
- **Popularidade (quartis de estrelas):** Repositorios mais populares publicam com mais frequencia e falham menos no CI, porque tem mais revisao e automacao.
- **Contribuidores (quartis):** Mais contribuidores aumentam a frequencia de deploy e tambem as falhas de CI, por haver mais mudancas concorrentes.
- **Idade do repositorio (quartis):** Repositorios mais antigos sao mais estaveis: CFR menor e recuperacao mais rapida, mas lead time maior.

## Grupos

- Linguagem: linguagens com pelo menos 20 repositorios; demais e vazias em 'Outras'.
- Popularidade (quartis de estrelas): cortes em 1059.00, 1117.50, 1165.25.
- Contribuidores (quartis): cortes em 24.00, 47.50, 95.00.
- Idade do repositorio (quartis): cortes em 1.84, 4.76, 7.74.

| Fator | Grupo | Repositórios |
|---|---|---:|
| Linguagem principal | Go | 42 |
| Linguagem principal | Python | 56 |
| Linguagem principal | Rust | 27 |
| Linguagem principal | TypeScript | 55 |
| Linguagem principal | Outras | 120 |
| Popularidade (quartis de estrelas) | Q1 | 76 |
| Popularidade (quartis de estrelas) | Q2 | 74 |
| Popularidade (quartis de estrelas) | Q3 | 75 |
| Popularidade (quartis de estrelas) | Q4 | 75 |
| Contribuidores (quartis) | Q1 | 77 |
| Contribuidores (quartis) | Q2 | 73 |
| Contribuidores (quartis) | Q3 | 76 |
| Contribuidores (quartis) | Q4 | 74 |
| Idade do repositorio (quartis) | Q1 | 75 |
| Idade do repositorio (quartis) | Q2 | 75 |
| Idade do repositorio (quartis) | Q3 | 75 |
| Idade do repositorio (quartis) | Q4 | 75 |

## Resultados

| Fator | Métrica | Teste | n | H/U | p | p Holm | Efeito | δ Q4 x Q1 |
|---|---|---|---:|---:|---:|---:|---|---|
| Linguagem principal | RQ01 deployment frequency | Kruskal-Wallis | 300 | 23.32 | 0.0001 | 0.0019 * | 0.078 (pequeno) |  |
| Linguagem principal | RQ02 lead time por release | Kruskal-Wallis | 300 | 23.28 | 0.0001 | 0.0019 * | 0.078 (pequeno) |  |
| Linguagem principal | RQ02 lead time por commit | Kruskal-Wallis | 300 | 17.11 | 0.0018 | 0.0258 * | 0.057 (pequeno) |  |
| Linguagem principal | RQ03 CFR(a) | Kruskal-Wallis | 300 | 5.20 | 0.2678 | 1.0000 | 0.017 (pequeno) |  |
| Linguagem principal | RQ03 CFR(b) | Kruskal-Wallis | 299 | 19.75 | 0.0006 | 0.0084 * | 0.066 (pequeno) |  |
| Linguagem principal | RQ04 tempo de recuperacao | Kruskal-Wallis | 261 | 8.83 | 0.0654 | 0.7849 | 0.034 (pequeno) |  |
| Popularidade (quartis de estrelas) | RQ01 deployment frequency | Kruskal-Wallis | 300 | 1.63 | 0.6529 | 1.0000 | 0.005 (desprezivel) | -0.113 (desprezivel) |
| Popularidade (quartis de estrelas) | RQ02 lead time por release | Kruskal-Wallis | 300 | 1.58 | 0.6637 | 1.0000 | 0.005 (desprezivel) | 0.006 (desprezivel) |
| Popularidade (quartis de estrelas) | RQ02 lead time por commit | Kruskal-Wallis | 300 | 0.77 | 0.8560 | 1.0000 | 0.003 (desprezivel) | 0.036 (desprezivel) |
| Popularidade (quartis de estrelas) | RQ03 CFR(a) | Kruskal-Wallis | 300 | 2.70 | 0.4409 | 1.0000 | 0.009 (desprezivel) | 0.009 (desprezivel) |
| Popularidade (quartis de estrelas) | RQ03 CFR(b) | Kruskal-Wallis | 299 | 0.69 | 0.8758 | 1.0000 | 0.002 (desprezivel) | -0.003 (desprezivel) |
| Popularidade (quartis de estrelas) | RQ04 tempo de recuperacao | Kruskal-Wallis | 261 | 0.16 | 0.9844 | 1.0000 | 0.001 (desprezivel) | -0.018 (desprezivel) |
| Contribuidores (quartis) | RQ01 deployment frequency | Kruskal-Wallis | 300 | 13.13 | 0.0044 | 0.0567 | 0.044 (pequeno) | -0.260 (pequeno) |
| Contribuidores (quartis) | RQ02 lead time por release | Kruskal-Wallis | 300 | 56.42 | < 0.0001 | < 0.0001 * | 0.189 (medio) | 0.616 (grande) |
| Contribuidores (quartis) | RQ02 lead time por commit | Kruskal-Wallis | 300 | 54.87 | < 0.0001 | < 0.0001 * | 0.184 (medio) | 0.598 (grande) |
| Contribuidores (quartis) | RQ03 CFR(a) | Kruskal-Wallis | 300 | 2.76 | 0.4308 | 1.0000 | 0.009 (desprezivel) | 0.098 (desprezivel) |
| Contribuidores (quartis) | RQ03 CFR(b) | Kruskal-Wallis | 299 | 22.75 | < 0.0001 | 0.0008 * | 0.076 (pequeno) | -0.398 (medio) |
| Contribuidores (quartis) | RQ04 tempo de recuperacao | Kruskal-Wallis | 261 | 1.22 | 0.7491 | 1.0000 | 0.005 (desprezivel) | -0.062 (desprezivel) |
| Idade do repositorio (quartis) | RQ01 deployment frequency | Kruskal-Wallis | 300 | 31.57 | < 0.0001 | < 0.0001 * | 0.106 (medio) | -0.502 (grande) |
| Idade do repositorio (quartis) | RQ02 lead time por release | Kruskal-Wallis | 300 | 70.46 | < 0.0001 | < 0.0001 * | 0.236 (medio) | 0.710 (grande) |
| Idade do repositorio (quartis) | RQ02 lead time por commit | Kruskal-Wallis | 300 | 71.62 | < 0.0001 | < 0.0001 * | 0.240 (medio) | 0.705 (grande) |
| Idade do repositorio (quartis) | RQ03 CFR(a) | Kruskal-Wallis | 300 | 6.93 | 0.0741 | 0.8155 | 0.023 (pequeno) | -0.034 (desprezivel) |
| Idade do repositorio (quartis) | RQ03 CFR(b) | Kruskal-Wallis | 299 | 36.69 | < 0.0001 | < 0.0001 * | 0.123 (medio) | -0.488 (grande) |
| Idade do repositorio (quartis) | RQ04 tempo de recuperacao | Kruskal-Wallis | 261 | 0.58 | 0.9016 | 1.0000 | 0.002 (desprezivel) | 0.036 (desprezivel) |

\* significativo após Holm (alfa 0.05). Testes significativos: **11** de 24.

## Escolha estatística

- As métricas são assimétricas e limitadas (CFR entre 0 e 1). Por isso os testes são não paramétricos: Kruskal-Wallis para três ou mais grupos e Mann-Whitney para dois.
- O tamanho de efeito do Kruskal-Wallis é ε² = H / (n − 1). Faixas de Tomczak e Tomczak (2014): < 0,01 desprezível; < 0,08 pequeno; < 0,26 médio; ≥ 0,26 grande.
- Nos fatores por quartil, o Cliff's delta entre Q4 e Q1 mostra a direção. δ positivo indica valores maiores no Q4. Faixas de Romano et al. (2006).
- Holm controla o erro de família nos 24 testes. Ausente não vira zero; o repositório só sai do teste daquela métrica.

## Limitações

- Estrelas e contribuidores foram lidos na data da coleta (`collected_at`), não no fim de 2025. A idade usa `created_at` até 2025-12-31.
- Contribuidores vêm do endpoint com `anon=true`. Ele conta e-mails anônimos e pode contar a mesma pessoa duas vezes.
- O tipo de projeto (biblioteca, aplicação, CLI) não entrou, porque exige rotulação manual dos 300 repositórios.
- A amostra só tem repositórios com pelo menos 5 releases e 50 workflow runs em 2025, então os grupos não representam todo o GitHub.
- A coleta percorreu as faixas de estrelas a partir de 1000, então a popularidade varia pouco na amostra. Os quartis de estrelas separam faixas estreitas e o teste tem pouco poder para esse fator.
- Os fatores estão correlacionados entre si, por exemplo estrelas e contribuidores. Cada teste olha um fator por vez e não isola o efeito de cada um.
- Associação não implica causa.
