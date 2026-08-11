"""Coleta e normalizacao dos repositorios populares."""


def collect_top_repositories(client, limit: int = 100) -> list[dict]:
    """Coleta os repositorios mais populares do GitHub."""
    raise NotImplementedError("Implementar coleta dos repositorios.")


def normalize_repository(raw_repository: dict) -> dict:
    """Normaliza os campos retornados pela API para o formato do CSV."""
    raise NotImplementedError("Implementar normalizacao dos campos.")
