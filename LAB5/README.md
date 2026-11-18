# LAB05 — Experimento em software real

Estrutura inicial para o experimento final sobre um software real, em operação
e de alto impacto. O objeto de estudo, a pergunta de pesquisa e o desenho serão
definidos pelo grupo na proposta.

## Estrutura

```text
LAB5/
├── config/                 # parâmetros do estudo e da coleta
├── data/
│   ├── raw/                # dados brutos e registros originais
│   ├── interim/            # dados validados e transformados
│   └── processed/          # datasets finais para a análise
├── docs/                   # proposta, método, ética e documentação final
├── notebooks/              # exploração e análises auxiliares
├── reports/
│   ├── figures/            # visualizações e gráficos finais
│   └── tables/             # tabelas e resultados estatísticos
├── dashboard/              # dashboard ou visualização final, se aplicável
├── src/lab05_real_software/ # coleta, validação, análise e impacto
└── tests/                  # testes automatizados e validações
```

O diretório `data/raw` deve preservar os registros originais. Dados pessoais,
credenciais e informações que não possam ser compartilhadas não devem ser
versionados.

## Sprints

- `Lab05S01`: proposta, evidências do software, GQM, categorias da pesquisa,
  plano de coleta/análise e coleta piloto.
- `Lab05S02`: coleta completa, validação, análise e ameaças à validade.
- `Lab05S03`: impacto, conclusões, limitações e rascunhos do documento e da
  apresentação.
- Documento final e apresentação: formato livre, conforme o enunciado.

## Critérios do estudo

O software escolhido deve ser real, estar em operação e ter alto impacto,
sempre com evidências e fontes. A coleta deve respeitar os termos de uso,
`robots.txt`, o limite de uma requisição por segundo para medições externas e
as regras de ética descritas no enunciado.
