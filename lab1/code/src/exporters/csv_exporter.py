"""Exportacao dos dados coletados para CSV."""

import csv
from pathlib import Path


FIELDNAMES = [
    "name_with_owner",
    "stargazer_count",
    "created_at",
    "repository_age_days",
    "merged_pull_requests",
    "updated_at",
    "days_since_last_update",
    "releases_count",
    "primary_language",
    "total_issues",
    "closed_issues",
    "closed_issues_ratio",
]


def _serialize_row(repository: dict) -> dict:
    """Converte valores None para string vazia no CSV."""
    row = dict(repository)
    if row.get("closed_issues_ratio") is None:
        row["closed_issues_ratio"] = ""
    return row


def export_repositories_csv(repositories: list[dict], output_path: str) -> None:
    """Exporta os repositorios normalizados para CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(_serialize_row(repository) for repository in repositories)
