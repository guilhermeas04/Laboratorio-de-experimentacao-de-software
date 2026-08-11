"""Cliente GraphQL simples para a API do GitHub."""


class GitHubGraphQLClient:
    """Encapsula requisicoes GraphQL ao GitHub."""

    def __init__(self, token: str, endpoint: str):
        self.token = token
        self.endpoint = endpoint

    def execute(self, query: str, variables: dict | None = None) -> dict:
        """Executa uma query GraphQL.

        A implementacao deve usar requisicao HTTP propria, sem bibliotecas
        especificas para a API do GitHub.
        """
        raise NotImplementedError("Implementar chamada GraphQL.")
