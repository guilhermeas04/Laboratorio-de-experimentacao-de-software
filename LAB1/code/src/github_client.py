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

        last_error: Exception | None = None

        for attempt in range(10):
            wait_seconds = min(60, 2 ** attempt)

            try:
                response = requests.post(
                    self.endpoint,
                    json={"query": query, "variables": variables or {}},
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "lab01-fpstats",
                    },
                    timeout=90,
                )
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(wait_seconds)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES:
                last_error = RuntimeError(f"HTTP {response.status_code}")
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()

            try:
                payload = response.json()
            except ValueError as exc:
                last_error = exc
                time.sleep(wait_seconds)
                continue

            if "errors" in payload:
                messages = "; ".join(
                    error.get("message", "") for error in payload["errors"]
                )
                last_error = RuntimeError(f"Erro GraphQL: {messages}")
                lowered = messages.lower()
                if any(
                    token in lowered
                    for token in ("timeout", "timed out", "something went wrong", "502")
                ):
                    time.sleep(wait_seconds)
                    continue
                raise last_error

            return payload["data"]

        raise RuntimeError(
            f"Falha ao consultar GraphQL apos varias tentativas: {last_error}"
        )
