"""Ponto de entrada integrado da coleta LAB3S01."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Sequence

from lab03_dora.api.github import GitHubClient
from lab03_dora.collection.history import (collect_many, release_change_rows,
                                            repositories_from_selection,
                                            update_selection_with_release_counts)
from lab03_dora.collection.observation import ObservationWindow
from lab03_dora.collection.selection import (SelectionCriteria, build_funnel,
                                              build_selection_table, read_csv,
                                              write_csv)
from lab03_dora.collection.workflow_runs import collect_workflow_runs_for_repositories
from lab03_dora.metrics.deployment_frequency import deployment_frequency
from lab03_dora.metrics.lead_time import release_changes, summarize_lead_time
from lab03_dora.metrics.reliability import calculate_cfr, calculate_recovery
from lab03_dora.pipeline.select_repositories import (DEFAULT_CONFIG, LAB3_ROOT,
                                                      collect_candidates, load_config)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _metrics(histories, workflow_results, window: ObservationWindow) -> list[dict]:
    end_dt = datetime.combine(window.end, time.max, tzinfo=UTC)
    changes = release_change_rows(histories)
    by_repo: dict[str, list] = {}
    for row in changes:
        if not row.get("published_at"):
            continue
        try:
            dates = json.loads(row.get("commit_authored_at") or "[]")
            item = release_changes(row["tag_name"], row["published_at"], dates,
                                   has_previous_release=str(row.get("has_previous_release")).lower() == "true")
            by_repo.setdefault(row["repository"], []).append(item)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    rows = []
    for history in histories:
        result = workflow_results.get(history.repository)
        runs = result.runs if result else []
        lead = summarize_lead_time(by_repo.get(history.repository, []))
        recoveries = calculate_recovery(runs, observation_end=end_dt)
        durations = [item.recovery_hours for item in recoveries.episodes if item.recovery_hours is not None]
        rows.append({
            "repository": history.repository,
            "release_count": history.primary_count,
            "deployment_frequency_per_week": deployment_frequency(history.primary_count, window.start, window.end),
            "lead_time_by_release_days": lead.by_release_days,
            "lead_time_by_commit_days": lead.by_commit_days,
            "valid_workflow_runs_count": len(runs),
            "cfr_ci": calculate_cfr(runs),
            "recovery_median_hours": statistics.median(durations) if durations else None,
            "recovery_censored_count": recoveries.censored_count,
        })
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Executa a coleta integrada da Sprint 1 (LAB3S01).")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--lab-root", type=Path, default=LAB3_ROOT)
    parser.add_argument("--input-csv", type=Path, help="Candidatos previamente coletados; evita a busca inicial.")
    parser.add_argument("--limit", type=int, default=None, help="Limite de repositorios (use 3 para smoke test).")
    parser.add_argument("--target-with-actions", type=int, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    root = args.lab_root
    window = ObservationWindow.from_config(config)
    selection_cfg = config.get("selection", {})
    criteria = SelectionCriteria(
        target_s01_sample_size=int(selection_cfg.get("target_s01_sample_size", 100)),
        minimum_releases=int(selection_cfg.get("minimum_releases", 5)),
        minimum_valid_workflow_runs=int(selection_cfg.get("minimum_valid_workflow_runs", 50)),
    )
    client = GitHubClient.from_environment(cache_dir=root / "cache" / "http")
    candidates = read_csv(args.input_csv) if args.input_csv else collect_candidates(
        config, limit=args.limit, target_with_actions=args.target_with_actions or criteria.target_s01_sample_size, client=client)
    selection = build_selection_table(candidates, criteria)
    write_csv(root / "data/interim/selection/candidate_repositories.csv", candidates)
    repos = repositories_from_selection(selection, limit=args.limit or criteria.target_s01_sample_size)
    histories = collect_many(client, repos, window=window, lab_root=root)
    selection = update_selection_with_release_counts(selection, histories, criteria)
    workflow = collect_workflow_runs_for_repositories(
        repos, datetime.combine(window.start, time.min, tzinfo=UTC),
        datetime.combine(window.end, time.max, tzinfo=UTC), client,
        cache_dir=root / "data/raw/workflow_runs")
    counts = {name: result.total_count for name, result in workflow.items()}
    selection = build_selection_table([{**row, "valid_workflow_runs_count": counts.get(row.get("full_name"))}
                                       for row in selection], criteria)
    write_csv(root / "data/interim/selection/s01_repository_selection.csv", selection)
    write_csv(root / "reports/funnel/s01_selection_funnel.csv", build_funnel(selection, criteria))
    metrics = _metrics(histories, workflow, window)
    write_csv(root / "data/processed/metrics/s01_metrics.csv", metrics)
    _write_json(root / "data/interim/workflow_runs/s01_workflow_runs.json",
                {name: {"runs": result.runs, "windows_at_limit": result.windows_at_limit} for name, result in workflow.items()})
    print(f"Pipeline concluido: {len(repos)} repositorios; metricas={root / 'data/processed/metrics/s01_metrics.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
