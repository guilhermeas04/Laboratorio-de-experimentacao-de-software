# Codigo do Lab01

Estrutura inicial para a Lab01S01.

## Pastas

- `src/queries/`: consultas GraphQL escritas pelo grupo.
- `src/collectors/`: scripts responsaveis por chamar a API do GitHub.
- `src/validators/`: validacoes rapidas por RQ.
- `src/exporters/`: exportacao de resultados e snapshots.
- `tests/`: testes automatizados ou amostras de validacao.

## Variaveis de ambiente previstas

Crie um arquivo `.env` local com base em `.env.example`.

```env
GITHUB_TOKEN=seu_token_aqui
GITHUB_GRAPHQL_URL=https://api.github.com/graphql
```

Nao versionar tokens reais.
