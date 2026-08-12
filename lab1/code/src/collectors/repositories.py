"""Coleta e normalizacao dos repositorios populares."""

from pathlib import Path


QUERY_PATH = Path(__file__).resolve().parents[1] / "queries" / "rq05_rq06_repositories.graphql"


def collect_top_repositories(client, limit: int = 100) -> list[dict]:
    """Coleta os repositorios mais populares do GitHub."""
    query = QUERY_PATH.read_text(encoding="utf-8")
    data = client.execute(query, {"first": limit})
    nodes = data["search"]["nodes"]

    return [normalize_repository(node) for node in nodes if node]


def normalize_repository(raw_repository: dict) -> dict:
    """Normaliza os campos retornados pela API para o formato do CSV."""
    primary_language = raw_repository.get("primaryLanguage")
    language_name = primary_language["name"] if primary_language else ""

    total_issues = raw_repository["issues"]["totalCount"]
    closed_issues = raw_repository["closedIssues"]["totalCount"]

    if total_issues > 0:
        closed_issues_ratio = closed_issues / total_issues
    else:
        # Sem issues, a razao e indefinida; o CSV recebe string vazia.
        closed_issues_ratio = None

    return {
        "name_with_owner": raw_repository["nameWithOwner"],
        "primary_language": language_name,
        "total_issues": total_issues,
        "closed_issues": closed_issues,
        "closed_issues_ratio": closed_issues_ratio,
    }
