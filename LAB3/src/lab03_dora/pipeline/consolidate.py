"""Dataset final da LAB3S02 a partir das metricas ja coletadas.

A heuristica de CFR(b) e a da issue #108. Este modulo nao chama a API.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from lab03_dora.collection.selection import SelectionCriteria, build_funnel, read_csv, write_csv
from lab03_dora.pipeline.select_repositories import LAB3_ROOT, load_config


TARGET_ELIGIBLE = 300
DATASET_COLUMNS = (
    "repository",
    "release_count",
    "deployment_frequency_per_week",
    "lead_time_by_release_days",
    "lead_time_by_commit_days",
    "valid_workflow_runs_count",
    "cfr_ci",
    "cfr_b",
    "cfr_b_evaluated_releases",
    "cfr_b_failed_releases",
    "cfr_b_censored_releases",
    "recovery_median_hours",
    "recovery_censored_count",
    "eligible",
    "exclusion_reason",
)
BLANK_IF_MISSING = {
    "lead_time_by_release_days",
    "lead_time_by_commit_days",
    "cfr_ci",
    "cfr_b",
    "cfr_b_evaluated_releases",
    "cfr_b_failed_releases",
    "cfr_b_censored_releases",
    "recovery_median_hours",
}


def deduplicate_rows(rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Mantem a primeira linha de cada repositorio."""

    seen: set[str] = set()
    kept: list[dict[str, Any]] = []
    dropped = 0
    for row in rows:
        name = str(row.get("repository") or "")
        if name in seen:
            dropped += 1
            continue
        seen.add(name)
        kept.append(dict(row))
    return kept, dropped


def _number(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def classify_row(row: dict[str, Any], criteria: SelectionCriteria) -> dict[str, Any]:
    """Marca elegibilidade. Lead time e CFR ausentes continuam vazios."""

    enriched = {column: row.get(column, "") for column in DATASET_COLUMNS}
    enriched["repository"] = str(row.get("repository") or "")
    releases = _number(row.get("release_count"))
    runs = _number(row.get("valid_workflow_runs_count"))
    reason = ""
    eligible = True
    if releases is None or releases < criteria.minimum_releases:
        eligible = False
        reason = "insufficient_releases"
    elif runs is None or runs < criteria.minimum_valid_workflow_runs:
        eligible = False
        reason = "insufficient_valid_workflow_runs"
    enriched["eligible"] = "true" if eligible else "false"
    enriched["exclusion_reason"] = reason
    for column in BLANK_IF_MISSING:
        if enriched.get(column) is None:
            enriched[column] = ""
    for column in ("release_count", "valid_workflow_runs_count", "recovery_censored_count"):
        if enriched.get(column) is None:
            enriched[column] = ""
    return enriched


def build_dataset(
    rows: Sequence[dict[str, Any]],
    criteria: SelectionCriteria,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    unique, dropped = deduplicate_rows(rows)
    dataset = [classify_row(row, criteria) for row in unique]
    eligible = sum(1 for row in dataset if row["eligible"] == "true")
    summary = {
        "rows": len(dataset),
        "duplicate_count": dropped,
        "eligible_count": eligible,
        "target_eligible": TARGET_ELIGIBLE,
        "target_met": eligible >= TARGET_ELIGIBLE,
    }
    return dataset, summary


def data_dictionary() -> list[dict[str, str]]:
    return [
        _entry("repository", "texto", "", "Nome completo owner/name.", "selecao GitHub", "Linha sem nome e descartada."),
        _entry("release_count", "inteiro", "releases", "Releases primarias publicadas na janela, sem draft e sem pre-release.", "coleta de releases", "Vazio se a coleta nao rodou. Zero significa que rodou e nao achou release."),
        _entry("deployment_frequency_per_week", "decimal", "releases/semana", "release_count dividido pelas semanas da janela, 365/7 em 2025.", "RQ01", "Vazio se release_count estiver vazio."),
        _entry("lead_time_by_release_days", "decimal", "dias", "Mediana, por release, de published_at menos o commit mais antigo do compare.", "RQ02 variante a", "Vazio se nao ha release anterior ou nao ha commit. Nao vira zero."),
        _entry("lead_time_by_commit_days", "decimal", "dias", "Mediana de published_at menos cada commit incluido nas releases.", "RQ02 variante b", "Vazio se nao ha commit valido. Nao vira zero."),
        _entry("valid_workflow_runs_count", "inteiro", "runs", "Workflow runs de push no default branch dentro da janela.", "coleta de workflow runs", "Vazio se a coleta nao rodou."),
        _entry("cfr_ci", "decimal", "proporcao", "Falhas de CI divididas por falhas mais sucessos. Cancelados ficam de fora.", "RQ03 variante a", "Vazio se nao ha run com sucesso ou falha."),
        _entry("cfr_b", "decimal", "proporcao", "Releases com corretiva em ate 7 dias, pela heuristica da #108, sobre as releases avaliadas.", "RQ03 variante b", "Vazio se a tabela de origem nao trouxe a coluna ou se nao ha release avaliavel."),
        _entry("cfr_b_evaluated_releases", "inteiro", "releases", "Releases primarias fora dos ultimos 7 dias da janela.", "heuristica #108", "Vazio quando cfr_b nao foi calculado."),
        _entry("cfr_b_failed_releases", "inteiro", "releases", "Releases avaliadas cuja seguinte e corretiva no prazo de 7 dias.", "heuristica #108", "Vazio quando cfr_b nao foi calculado."),
        _entry("cfr_b_censored_releases", "inteiro", "releases", "Releases dos ultimos 7 dias da janela. Ficam fora do CFR(b).", "heuristica #108", "Vazio quando cfr_b nao foi calculado."),
        _entry("recovery_median_hours", "decimal", "horas", "Mediana do tempo entre a primeira falha de um workflow e o proximo sucesso.", "RQ04", "Vazio se nao ha episodio recuperado. Nao vira zero."),
        _entry("recovery_censored_count", "inteiro", "episodios", "Episodios de falha sem sucesso ate o fim da janela.", "RQ04", "Vazio se a coleta de runs nao rodou."),
        _entry("eligible", "booleano", "", "true quando release_count >= 5 e valid_workflow_runs_count >= 50.", "criterio de inclusao", "Nao se aplica."),
        _entry("exclusion_reason", "texto", "", "insufficient_releases ou insufficient_valid_workflow_runs.", "funil", "Vazio quando eligible e true."),
    ]


def _entry(column: str, kind: str, unit: str, definition: str, origin: str, missing: str) -> dict[str, str]:
    return {
        "coluna": column,
        "tipo": kind,
        "unidade": unit,
        "definicao": definition,
        "origem": origin,
        "ausentes": missing,
    }


def write_outputs(
    *,
    lab_root: Path,
    metrics_path: Path,
    selection_path: Path,
    criteria: SelectionCriteria,
    window: dict[str, str],
) -> dict[str, Any]:
    metrics = read_csv(metrics_path)
    dataset, summary = build_dataset(metrics, criteria)
    dataset_path = lab_root / "data" / "processed" / "datasets" / "s02_metrics.csv"
    dictionary_path = lab_root / "data" / "processed" / "datasets" / "s02_data_dictionary.csv"
    funnel_path = lab_root / "reports" / "funnel" / "s02_selection_funnel.csv"
    manifest_path = lab_root / "data" / "processed" / "datasets" / "s02_manifest.json"
    write_csv(dataset_path, dataset, fieldnames=DATASET_COLUMNS)
    write_csv(dictionary_path, data_dictionary(), fieldnames=("coluna", "tipo", "unidade", "definicao", "origem", "ausentes"))
    if selection_path.exists():
        funnel = build_funnel(read_csv(selection_path), criteria)
    else:
        funnel = []
    funnel.append({
        "stage": "metrics_rows",
        "count": summary["rows"],
        "discarded": summary["duplicate_count"],
        "description": "Linhas do dataset apos remover repositorio duplicado.",
    })
    funnel.append({
        "stage": "eligible_final",
        "count": summary["eligible_count"],
        "discarded": summary["rows"] - summary["eligible_count"],
        "description": f"Repositorios com pelo menos {criteria.minimum_releases} releases e {criteria.minimum_valid_workflow_runs} workflow runs validos. Alvo {TARGET_ELIGIBLE}.",
    })
    write_csv(funnel_path, funnel, fieldnames=("stage", "count", "discarded", "description"))
    manifest = {
        "issue": 109,
        "observation_window": window,
        "heuristic": "docs/cfr-b-heuristica.md",
        "source_metrics": str(metrics_path),
        "dataset": str(dataset_path.relative_to(lab_root)),
        "dictionary": str(dictionary_path.relative_to(lab_root)),
        "funnel": str(funnel_path.relative_to(lab_root)),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        **summary,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Consolida o dataset final da LAB3S02.")
    parser.add_argument("--lab-root", type=Path, default=LAB3_ROOT)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--selection", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.lab_root
    config_path = args.config or (root / "config" / "lab3s02.json")
    config = load_config(config_path) if config_path.exists() else load_config(root / "config" / "lab3s01.json")
    selection_cfg = config.get("selection", {})
    criteria = SelectionCriteria(
        target_s01_sample_size=int(selection_cfg.get("target_final_sample_size", TARGET_ELIGIBLE)),
        minimum_releases=int(selection_cfg.get("minimum_releases", 5)),
        minimum_valid_workflow_runs=int(selection_cfg.get("minimum_valid_workflow_runs", 50)),
    )
    window = config.get("observation_window", {"start": "2025-01-01", "end": "2025-12-31"})
    manifest = write_outputs(
        lab_root=root,
        metrics_path=args.metrics or (root / "data" / "processed" / "metrics" / "s01_metrics.csv"),
        selection_path=args.selection or (root / "data" / "interim" / "selection" / "s01_repository_selection.csv"),
        criteria=criteria,
        window=window,
    )
    print(
        f"Dataset S02: {manifest['rows']} repositorios, {manifest['eligible_count']} elegiveis, "
        f"{manifest['duplicate_count']} duplicatas. Alvo {manifest['target_eligible']} atingido: {manifest['target_met']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
