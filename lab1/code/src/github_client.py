"""Cliente GraphQL simples para a API do GitHub."""

import time

import requests


RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


class GitHubGraphQLClient:
    """Encapsula requisicoes GraphQL ao GitHub."""

    def __init__(self, token: str, endpoint: str):
        self.token = token
        self.endpoint = endpoint

    def execute(self, query: str, variables: dict | None = None) -> dict:
        """Executa uma query GraphQL.

        Usa HTTP direto com `requests`, sem bibliotecas especificas para a API
        do GitHub, conforme a regra do laboratorio.
        """
        if not self.token:
            raise ValueError("GITHUB_TOKEN nao configurado.")

        response = None

        for attempt in range(3):
            response = requests.post(
                self.endpoint,
                json={"query": query, "variables": variables or {}},
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "lab01-fpstats",
                },
                timeout=30,
            )

            if response.status_code not in RETRYABLE_STATUS_CODES:
                break

            time.sleep(2**attempt)

        response.raise_for_status()
        payload = response.json()

        if "errors" in payload:
            messages = "; ".join(error.get("message", "") for error in payload["errors"])
            raise RuntimeError(f"Erro GraphQL: {messages}")

        return payload["data"]
