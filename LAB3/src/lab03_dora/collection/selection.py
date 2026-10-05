"""Selection funnel and S01 sampling helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class SelectionCriteria:
    target_s01_sample_size: int = 100
    minimum_releases: int = 5
    minimum_valid_workflow_runs: int = 50


FUNNEL_COLUMNS = ("stage", "count", "discarded", "description")


def classify_repository(row: dict[str, Any], criteria: SelectionCriteria) -> tuple[str, str]:
    """Classify a candidate according to the available selection evidence."""

    if _as_bool(row.get("archived")):
        return "discarded", "archived"
    if _as_bool(row.get("disabled")):
        return "discarded", "disabled"
    if not _as_bool(row.get("has_actions")):
        return "discarded", "no_github_actions"

    releases_count = _as_optional_int(row.get("releases_count"))
    if releases_count is not None and releases_count < criteria.minimum_releases:
        return "discarded", "insufficient_releases"

    runs_count = _as_optional_int(row.get("valid_workflow_runs_count"))
    if runs_count is not None and runs_count < criteria.minimum_valid_workflow_runs:
        return "discarded", "insufficient_valid_workflow_runs"

    if releases_count is None or runs_count is None:
        return "pending_downstream_collection", "requires_releases_or_workflow_runs_collection"
    return "eligible_s01", ""


def build_selection_table(
    rows: Iterable[dict[str, Any]],
    criteria: SelectionCriteria,
) -> list[dict[str, Any]]:
    """Add selection status/reason to candidate rows."""

    selected: list[dict[str, Any]] = []
    eligible_count = 0
    base_sample_count = 0
    for row in rows:
        enriched = dict(row)
        status, reason = classify_repository(enriched, criteria)
        if status == "pending_downstream_collection" and base_sample_count < criteria.target_s01_sample_size:
            status = "s01_base_sample"
            reason = "awaiting_releases_and_workflow_runs_counts"
            base_sample_count += 1
        elif status == "pending_downstream_collection":
            status, reason = "discarded", "sample_limit_reached"
        if status == "eligible_s01" and eligible_count >= criteria.target_s01_sample_size:
            status, reason = "discarded", "sample_limit_reached"
        if status == "eligible_s01":
            eligible_count += 1
        enriched["selection_status"] = status
        enriched["exclusion_reason"] = reason
        selected.append(enriched)
    return selected


def build_funnel(rows: Iterable[dict[str, Any]], criteria: SelectionCriteria) -> list[dict[str, Any]]:
    """Build a reproducible selection funnel from candidate rows."""

    materialized = list(rows)
    active = [row for row in materialized if not _as_bool(row.get("archived")) and not _as_bool(row.get("disabled"))]
    with_actions = [row for row in active if _as_bool(row.get("has_actions"))]
    with_release_evidence = [
        row
        for row in with_actions
        if _as_optional_int(row.get("releases_count")) is None
        or _as_optional_int(row.get("releases_count")) >= criteria.minimum_releases
    ]
    with_run_evidence = [
        row
        for row in with_release_evidence
        if _as_optional_int(row.get("valid_workflow_runs_count")) is None
        or _as_optional_int(row.get("valid_workflow_runs_count")) >= criteria.minimum_valid_workflow_runs
    ]
    eligible = [row for row in materialized if row.get("selection_status") == "eligible_s01"]
    base_sample = [row for row in materialized if row.get("selection_status") == "s01_base_sample"]
    pending = [row for row in materialized if row.get("selection_status") == "pending_downstream_collection"]

    stages = [
        ("candidates", len(materialized), "Repositorios retornados pela busca inicial."),
        ("active_repositories", len(active), "Repositorios nao arquivados e nao desabilitados."),
        ("with_github_actions", len(with_actions), "Repositorios com ao menos um workflow do GitHub Actions."),
        (
            "with_minimum_releases",
            len(with_release_evidence),
            f"Repositorios com evidencia de pelo menos {criteria.minimum_releases} releases, quando a contagem ja existe.",
        ),
        (
            "with_minimum_workflow_runs",
            len(with_run_evidence),
            f"Repositorios com evidencia de pelo menos {criteria.minimum_valid_workflow_runs} workflow runs validos, quando a contagem ja existe.",
        ),
        (
            "s01_base_sample",
            len(base_sample),
            f"Base da Sprint 1 com repositorios que usam GitHub Actions, limitada a {criteria.target_s01_sample_size}, aguardando contagens de releases e workflow runs.",
        ),
        (
            "eligible_s01_sample",
            len(eligible),
            f"Repositorios elegiveis selecionados para a amostra S01, limitado a {criteria.target_s01_sample_size}.",
        ),
        (
            "pending_downstream_collection",
            len(pending),
            "Repositorios com Actions que ainda dependem das coletas de releases/workflow runs das issues seguintes.",
        ),
    ]

    previous = 0
    funnel: list[dict[str, Any]] = []
    for index, (stage, count, description) in enumerate(stages):
        discarded = 0 if index == 0 else max(previous - count, 0)
        funnel.append(
            {
                "stage": stage,
                "count": count,
                "discarded": discarded,
                "description": description,
            }
        )
        previous = count
    return funnel


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: Iterable[str] | None = None) -> None:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        ordered: list[str] = []
        for row in materialized:
            for key in row:
                if key not in ordered:
                    ordered.append(key)
        fieldnames = ordered
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(materialized)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "sim"}


def _as_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
