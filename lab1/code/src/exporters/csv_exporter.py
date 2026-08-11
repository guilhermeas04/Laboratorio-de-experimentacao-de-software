"""Exportacao dos dados coletados para CSV."""

import csv
from pathlib import Path


FIELDNAMES = [
    "name_with_owner",
    "created_at",
    "repository_age_days",
    "merged_pull_requests",
]


def export_repositories_csv(repositories: list[dict], output_path: str) -> None:
    """Exporta os repositorios normalizados para CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(repositories)
