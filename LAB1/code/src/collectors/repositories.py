"""Coleta e normalizacao dos repositorios populares."""

from datetime import UTC, datetime
from pathlib import Path
import time


QUERY_PATH = Path(__file__).resolve().parents[1] / "queries" / "top_repositories.graphql"
PAGE_SIZE = 25


def collect_top_repositories(client, limit: int = 1000) -> list[dict]:
    """Coleta repositorios populares com paginacao e sem duplicatas."""
    query = QUERY_PATH.read_text(encoding="utf-8")
    repositories: list[dict] = []
    seen: set[str] = set()
    cursor = None

    while len(repositories) < limit:
        data = client.execute(query, {"first": PAGE_SIZE, "after": cursor})
        search = data["search"]
        page_nodes = [node for node in search["nodes"] if node]

        if not page_nodes:
            break

        for node in page_nodes:
            name = node["nameWithOwner"]
            if name in seen:
                continue

            seen.add(name)
            repositories.append(normalize_repository(node))
            if len(repositories) >= limit:
                break

        page_info = search["pageInfo"]
        if not page_info["hasNextPage"] or not page_info["endCursor"]:
            break

        cursor = page_info["endCursor"]
        time.sleep(0.3)

    if len(repositories) != limit:
        raise RuntimeError(
            f"Esperados {limit} repositorios unicos, obtidos {len(repositories)}."
        )

    return repositories


def normalize_repository(raw_repository: dict) -> dict:
    """Normaliza os campos da consulta unica para o formato do CSV."""
    now = datetime.now(UTC)

    created_at = raw_repository["createdAt"]
    created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    repository_age_days = (now - created_date).days

    updated_at = raw_repository["updatedAt"]
    updated_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    days_since_last_update = (now - updated_date).days

    primary_language = raw_repository.get("primaryLanguage")
    language_name = primary_language["name"] if primary_language else ""

    total_issues = raw_repository["issues"]["totalCount"]
    closed_issues = raw_repository["closedIssues"]["totalCount"]

    if total_issues > 0:
        closed_issues_ratio = closed_issues / total_issues
    else:
        closed_issues_ratio = None

    return {
        "name_with_owner": raw_repository["nameWithOwner"],
        "stargazer_count": raw_repository["stargazerCount"],
        "created_at": created_at,
        "repository_age_days": repository_age_days,
        "merged_pull_requests": raw_repository["pullRequests"]["totalCount"],
        "updated_at": updated_at,
        "days_since_last_update": days_since_last_update,
        "releases_count": raw_repository["releases"]["totalCount"],
        "primary_language": language_name,
        "total_issues": total_issues,
        "closed_issues": closed_issues,
        "closed_issues_ratio": closed_issues_ratio,
    }
