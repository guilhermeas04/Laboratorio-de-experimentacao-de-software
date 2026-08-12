"""Coleta e normalizacao dos repositorios populares."""

from datetime import UTC, datetime
from pathlib import Path


QUERY_PATH = Path(__file__).resolve().parents[1] / "queries" / "rq03_rq04_repositories.graphql"


def collect_top_repositories(client, limit: int = 100) -> list[dict]:
    """Coleta os repositorios mais populares do GitHub."""
    query = QUERY_PATH.read_text(encoding="utf-8")
    data = client.execute(query, {"first": limit})
    nodes = data["search"]["nodes"]

    return [normalize_repository(node) for node in nodes if node]


def normalize_repository(raw_repository: dict) -> dict:
    """Normaliza os campos retornados pela API para o formato do CSV."""
    updated_at = raw_repository["updatedAt"]
    updated_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    now = datetime.now(UTC)
    days_since_last_update = (now - updated_date).days

    return {
        "name_with_owner": raw_repository["nameWithOwner"],
        "updated_at": updated_at,
        "days_since_last_update": days_since_last_update,
        "releases_count": raw_repository["releases"]["totalCount"],
    }
