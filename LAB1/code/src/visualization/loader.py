"""Carregador unico do CSV consolidado de 1000 repositorios."""

from __future__ import annotations

import csv
from pathlib import Path


DEFAULT_CSV_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "processed" / "top_repositories.csv"
)

EXPECTED_COUNT = 1000

REQUIRED_COLUMNS = (
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
)

INTEGER_COLUMNS = (
    "stargazer_count",
    "repository_age_days",
    "merged_pull_requests",
    "days_since_last_update",
    "days_since_last_push",
    "releases_count",
    "total_issues",
    "closed_issues",
)

FLOAT_COLUMNS = ("closed_issues_ratio",)

STRING_COLUMNS = (
    "name_with_owner",
    "created_at",
    "updated_at",
    "pushed_at",
    "primary_language",
)


def _parse_int(value: str, field: str, row_number: int) -> int:
    if value is None or value == "":
        raise ValueError(f"linha {row_number}: campo `{field}` vazio")
    try:
        return int(float(value))
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"linha {row_number}: campo `{field}` invalido: {value!r}"
        ) from error


def _parse_optional_float(value: str, field: str, row_number: int) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"linha {row_number}: campo `{field}` invalido: {value!r}"
        ) from error


def validate_columns(fieldnames: list[str] | None) -> None:
    """Garante que o CSV possui todas as colunas esperadas."""
    if not fieldnames:
        raise ValueError("CSV sem cabecalho.")

    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        raise ValueError(f"Colunas ausentes no CSV: {', '.join(missing)}")


def validate_repositories(
    repositories: list[dict],
    expected_count: int = EXPECTED_COUNT,
) -> None:
    """Valida quantidade, colunas e tipos basicos dos registros."""
    if len(repositories) != expected_count:
        raise ValueError(
            f"Esperados {expected_count} repositorios, recebidos {len(repositories)}."
        )

    names = [repository["name_with_owner"] for repository in repositories]
    if len(set(names)) != len(names):
        raise ValueError("CSV possui name_with_owner duplicado.")

    for index, repository in enumerate(repositories, start=2):
        name = repository.get("name_with_owner")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"linha {index}: name_with_owner ausente")

        for field in INTEGER_COLUMNS:
            value = repository[field]
            if not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"linha {index}: `{field}` deve ser inteiro >= 0, recebido {value!r}"
                )

        ratio = repository["closed_issues_ratio"]
        if ratio is not None and (
            not isinstance(ratio, float) or ratio < 0 or ratio > 1
        ):
            raise ValueError(
                f"linha {index}: closed_issues_ratio fora de [0, 1]: {ratio!r}"
            )

        language = repository.get("primary_language")
        if language is not None and not isinstance(language, str):
            raise ValueError(f"linha {index}: primary_language invalido")

        for field in ("created_at", "updated_at", "pushed_at"):
            value = repository.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"linha {index}: `{field}` ausente")


def load_top_repositories(
    csv_path: Path | None = None,
    expected_count: int = EXPECTED_COUNT,
) -> list[dict]:
    """Carrega e valida o CSV consolidado antes de gerar graficos."""
    path = Path(csv_path) if csv_path is not None else DEFAULT_CSV_PATH
    if not path.exists():
        raise FileNotFoundError(f"CSV nao encontrado: {path}")

    with path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        validate_columns(reader.fieldnames)

        repositories: list[dict] = []
        for row_number, row in enumerate(reader, start=2):
            repository = {
                "name_with_owner": (row.get("name_with_owner") or "").strip(),
                "created_at": (row.get("created_at") or "").strip(),
                "updated_at": (row.get("updated_at") or "").strip(),
                "pushed_at": (row.get("pushed_at") or "").strip(),
                "primary_language": (row.get("primary_language") or "").strip() or None,
            }

            for field in INTEGER_COLUMNS:
                repository[field] = _parse_int(row.get(field, ""), field, row_number)

            for field in FLOAT_COLUMNS:
                repository[field] = _parse_optional_float(
                    row.get(field, ""), field, row_number
                )

            repositories.append(repository)

    validate_repositories(repositories, expected_count=expected_count)
    return repositories
