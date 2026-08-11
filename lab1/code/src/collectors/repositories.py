"""Coleta e normalizacao dos repositorios populares."""

from datetime import UTC, datetime
from pathlib import Path


QUERY_PATH = Path(__file__).resolve().parents[1] / "queries" / "rq01_rq02_repositories.graphql"


def collect_top_repositories(client, limit: int = 100) -> list[dict]:
    """Coleta os repositorios mais populares do GitHub."""
    query = QUERY_PATH.read_text(encoding="utf-8")
    data = client.execute(query, {"first": limit})
    nodes = data["search"]["nodes"]

    return [normalize_repository(node) for node in nodes if node]


def normalize_repository(raw_repository: dict) -> dict:
    """Normaliza os campos retornados pela API para o formato do CSV."""
    created_at = raw_repository["createdAt"]
    created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = datetime.now(UTC)
    repository_age_days = (now - created_date).days

    return {
        "name_with_owner": raw_repository["nameWithOwner"],
        "created_at": created_at,
        "repository_age_days": repository_age_days,
        "merged_pull_requests": raw_repository["pullRequests"]["totalCount"],
    }
