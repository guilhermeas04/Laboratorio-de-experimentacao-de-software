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
    "pushed_at",
    "days_since_last_push",
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
    if row.get("days_since_last_push") is None:
        row["days_since_last_push"] = ""
    if row.get("pushed_at") is None:
        row["pushed_at"] = ""
    return row


def export_repositories_csv(repositories: list[dict], output_path: str) -> None:
    """Exporta os repositorios normalizados para CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(_serialize_row(repository) for repository in repositories)


def validate_exported_csv(output_path: str, expected_count: int = 1000) -> None:
    """Valida quantidade, cabecalho, unicidade e campos basicos do CSV."""
    path = Path(output_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV nao encontrado: {path}")

    with path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != FIELDNAMES:
            raise ValueError(
                f"Cabecalho invalido.\nEsperado: {FIELDNAMES}\nRecebido: {reader.fieldnames}"
            )

        rows = list(reader)

    if len(rows) != expected_count:
        raise ValueError(
            f"CSV deveria ter {expected_count} linhas de dados, tem {len(rows)}."
        )

    names = [row.get("name_with_owner", "").strip() for row in rows]
    if any(not name for name in names):
        raise ValueError("Existem repositorios sem name_with_owner no CSV.")

    if len(set(names)) != len(names):
        raise ValueError("O CSV contem repositorios duplicados.")

    required_fields = [
        "stargazer_count",
        "created_at",
        "repository_age_days",
        "merged_pull_requests",
        "updated_at",
        "days_since_last_update",
        "releases_count",
        "total_issues",
        "closed_issues",
    ]

    for index, row in enumerate(rows, start=1):
        for field in required_fields:
            if row.get(field, "") == "":
                raise ValueError(
                    f"Linha {index} ({row.get('name_with_owner')}): "
                    f"campo obrigatorio ausente: {field}."
                )

    print(
        f"CSV validado: {expected_count} repositorios unicos e cabecalho completo."
    )
