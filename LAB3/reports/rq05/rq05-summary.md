# RQ05 - Frequência de deploy e taxa de falha

Repositórios no dataset: **300**. Correlação de Spearman entre `deployment_frequency_per_week` e cada variante de CFR.

| Variante | n usado | Ausentes | rho | IC 95% | p-valor | Força | Direção |
|---|---:|---:|---:|---|---:|---|---|
| cfr_a | 300 | 0 | -0.066 | [-0.178; 0.043] | 0.2546 | desprezivel | negativa |
| cfr_b | 299 | 1 | 0.524 | [0.434; 0.605] | < 0.0001 | forte | positiva |

## Escolha estatística

- Spearman mede associação monotônica pelos postos. Não exige normalidade nem relação linear. As duas métricas são assimétricas e o CFR fica preso entre 0 e 1.
- Empates recebem posto médio. A frequência tem poucos valores distintos, porque é a contagem de releases dividida por 365/7.
- O p-valor é bicaudal, com alfa 0,05. O intervalo de confiança vem de bootstrap percentil com semente fixa.
- Par com valor ausente sai da conta. Ausente não vira zero. A lista está em `rq05-missing.csv`.

## Limitações

- Correlação não implica causalidade. Tamanho, domínio e cultura do projeto podem afetar as duas métricas.
- A amostra só tem repositórios com pelo menos 5 releases e 50 workflow runs em 2025. Projetos que publicam pouco ficaram de fora, o que restringe a faixa da frequência.
- CFR(a) mede falha de CI no default branch, não falha em produção. CFR(b) depende da heurística de release corretiva, com F1 0,40 na validação manual.
- CFR(b) não é independente da frequência. Quem publica mais tem intervalos menores entre releases, então a próxima release cai mais vezes na janela de 7 dias. Parte da correlação de CFR(b) pode vir da própria definição, não de mais falhas.
- Repositório com poucas releases gera CFR(b) com poucos valores possíveis, o que cria empates.
- Os gráficos usam eixo X em escala logarítmica.
