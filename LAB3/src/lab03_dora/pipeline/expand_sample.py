"""Amplia a amostra ate 300 repositorios elegiveis e grava o dataset da #109.

Um repositorio elegivel tem, na janela, pelo menos 5 releases primarias e 50
workflow runs de push no default branch. A busca so usa a API REST propria.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time as dt_time
from pathlib import Path
from typing import Any, Sequence

from lab03_dora.api.github import GitHubApiError, GitHubClient
from lab03_dora.collection.commits import collect_commits_between
from lab03_dora.collection.history import ReleaseHistory, release_change_rows
from lab03_dora.collection.observation import ObservationWindow
from lab03_dora.collection.releases import normalize_release, pair_with_previous
from lab03_dora.collection.selection import write_csv
from lab03_dora.collection.workflow_runs import (
    CollectionResult,
    WorkflowRunClient,
    collect_workflow_runs,
    normalize_workflow_run,
)
from lab03_dora.metrics.cfr import calculate_cfr_b
from lab03_dora.metrics.deployment_frequency import deployment_frequency
from lab03_dora.metrics.lead_time import release_changes, summarize_lead_time
from lab03_dora.metrics.reliability import calculate_cfr, calculate_recovery
from lab03_dora.pipeline.consolidate import DATASET_COLUMNS, TARGET_ELIGIBLE

MAX_PRIMARY_RELEASES = 60
from lab03_dora.pipeline.select_repositories import LAB3_ROOT, load_config


def split_star_range(spec: str) -> list[str]:
    """Parte uma faixa de estrelas que estourou o teto de 1000 da busca."""

    if spec.endswith("..*"):
        start = int(spec[:-3])
        return [f"{start}..{start + 4999}", f"{start + 5000}..*"]
    start_text, end_text = spec.split("..", 1)
    start, end = int(start_text), int(end_text)
    if end - start < 1:
        return [spec]
    middle = (start + end) // 2
    return [f"{start}..{middle}", f"{middle + 1}..{end}"]


def _state_path(root: Path) -> Path:
    return root / "data" / "interim" / "s02_expand" / "state.json"


def _load_state(root: Path) -> dict[str, Any]:
    path = _state_path(root)
    if not path.exists():
        return {
            "seen": [],
            "eligible": [],
            "funnel": {
                "candidates": 0,
                "with_workflow_runs": 0,
                "with_releases": 0,
                "eligible": 0,
                "duplicates": 0,
                "errors": 0,
            },
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(root: Path, state: dict[str, Any]) -> None:
    path = _state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_dataset(root, state)


def _write_dataset(root: Path, state: dict[str, Any]) -> None:
    rows = state["eligible"]
    dataset = root / "data" / "processed" / "datasets" / "s02_metrics.csv"
    write_csv(dataset, rows, fieldnames=DATASET_COLUMNS)
    funnel = root / "reports" / "funnel" / "s02_selection_funnel.csv"
    counts = state["funnel"]
    write_csv(
        funnel,
        [
            {"stage": "candidates", "count": counts["candidates"], "discarded": 0, "description": "Repositorios retornados pela busca, com push em 2025."},
            {"stage": "with_minimum_workflow_runs", "count": counts["with_workflow_runs"], "discarded": counts["candidates"] - counts["with_workflow_runs"], "description": "Pelo menos 50 workflow runs de push no default branch, dentro da janela."},
            {"stage": "with_minimum_releases", "count": counts["with_releases"], "discarded": counts["with_workflow_runs"] - counts["with_releases"], "description": "Pelo menos 5 releases primarias dentro da janela."},
            {"stage": "eligible_final", "count": counts["eligible"], "discarded": counts["duplicates"], "description": "Amostra final, sem repositorio duplicado."},
            {"stage": "release_cap_skipped", "count": counts.get("release_cap_skipped", 0), "discarded": counts.get("release_cap_skipped", 0), "description": "Repositorios com mais de 60 releases primarias na janela. O compare de cada release estoura a cota da API, entao ficam fora da amostra."},
            {"stage": "errors", "count": counts["errors"], "discarded": 0, "description": "Repositorios cuja consulta falhou e nao entraram na amostra."},
        ],
        fieldnames=("stage", "count", "discarded", "description"),
    )
    manifest = {
        "issue": 109,
        "observation_window": {"start": "2025-01-01", "end": "2025-12-31"},
        "heuristic": "docs/cfr-b-heuristica.md",
        "dataset": "data/processed/datasets/s02_metrics.csv",
        "dictionary": "data/processed/datasets/s02_data_dictionary.csv",
        "funnel": "reports/funnel/s02_selection_funnel.csv",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "rows": len(rows),
        "duplicate_count": counts["duplicates"],
        "eligible_count": counts["eligible"],
        "target_eligible": TARGET_ELIGIBLE,
        "target_met": counts["eligible"] >= TARGET_ELIGIBLE,
        "candidates_screened": counts["candidates"],
    }
    path = root / "data" / "processed" / "datasets" / "s02_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _run_count(client: GitHubClient, repository: str, branch: str) -> int:
    payload = client.get(
        f"/repos/{repository}/actions/runs",
        {
            "branch": branch,
            "event": "push",
            "status": "completed",
            "created": "2025-01-01..2025-12-31",
            "per_page": 1,
        },
    ).payload
    if not isinstance(payload, dict):
        return 0
    return int(payload.get("total_count") or 0)


def _collect_runs_fast(
    client: GitHubClient,
    repository: str,
    branch: str,
    window: ObservationWindow,
    runs_client: WorkflowRunClient,
    cache_dir: Path,
) -> CollectionResult:
    """Um pedido cobre o ano inteiro. Meses separados so se a API corta em 1000."""

    created = f"{window.start.isoformat()}..{window.end.isoformat()}"
    params = {"branch": branch, "event": "push", "status": "completed", "created": created, "per_page": 100, "page": 1}
    first = client.get(f"/repos/{repository}/actions/runs", params).payload
    if not isinstance(first, dict):
        return CollectionResult(runs=[], windows_at_limit=[])
    total = int(first.get("total_count") or 0)
    if total >= 1000:
        return collect_workflow_runs(
            repository,
            branch,
            datetime.combine(window.start, dt_time.min, tzinfo=UTC),
            datetime.combine(window.end, dt_time.max, tzinfo=UTC),
            runs_client,
            cache_dir=cache_dir,
            workers=6,
        )
    collected: list[dict[str, Any]] = []
    page = 1
    payload: dict[str, Any] | Any = first
    while isinstance(payload, dict):
        for raw in payload.get("workflow_runs") or []:
            if not isinstance(raw, dict):
                continue
            normalized = normalize_workflow_run(
                raw,
                repository=repository,
                observation_month=str(raw.get("created_at") or "")[:7],
                default_branch=branch,
            )
            if normalized is not None:
                collected.append(normalized)
        runs_in_page = payload.get("workflow_runs") or []
        if page * 100 >= total or not runs_in_page or len(runs_in_page) < 100:
            break
        page += 1
        payload = client.get(f"/repos/{repository}/actions/runs", {**params, "page": page}).payload
    return CollectionResult(runs=collected, windows_at_limit=[])


def _has_minimum_releases(client: GitHubClient, repository: str, branch: str, window: ObservationWindow) -> bool:
    count = 0
    for page in range(1, 6):
        payload = client.get(f"/repos/{repository}/releases", {"per_page": 100, "page": page}).payload
        if not isinstance(payload, list) or not payload:
            break
        oldest = ""
        for item in payload:
            if not isinstance(item, dict):
                continue
            record = normalize_release(item, repository=repository, default_branch=branch, window=window)
            if record.primary:
                count += 1
            if record.published_at:
                oldest = record.published_at
        if count >= 5:
            return True
        if oldest and oldest < "2025-01-01":
            break
        if len(payload) < 100:
            break
    return False


def _metric_row(history, runs: list[dict], window: ObservationWindow) -> dict[str, Any]:
    end_dt = datetime.combine(window.end, dt_time.max, tzinfo=UTC)
    changes = release_change_rows([history])
    items = []
    for row in changes:
        if not row.get("published_at"):
            continue
        try:
            dates = json.loads(row.get("commit_authored_at") or "[]")
            items.append(
                release_changes(
                    row["tag_name"],
                    row["published_at"],
                    dates,
                    has_previous_release=str(row.get("has_previous_release")).lower() == "true",
                )
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    lead = summarize_lead_time(items)
    cfr_b = calculate_cfr_b(history.releases, history.compares, observation_end=end_dt)
    recoveries = calculate_recovery(runs, observation_end=end_dt)
    durations = [item.recovery_hours for item in recoveries.episodes if item.recovery_hours is not None]
    frequency = deployment_frequency(history.primary_count, window.start, window.end)
    cfr_ci = calculate_cfr(runs)
    return {
        "repository": history.repository,
        "release_count": history.primary_count,
        "deployment_frequency_per_week": "" if frequency is None else frequency,
        "lead_time_by_release_days": "" if lead.by_release_days is None else lead.by_release_days,
        "lead_time_by_commit_days": "" if lead.by_commit_days is None else lead.by_commit_days,
        "valid_workflow_runs_count": len(runs),
        "cfr_ci": "" if cfr_ci is None else cfr_ci,
        "cfr_b": "" if cfr_b.cfr is None else cfr_b.cfr,
        "cfr_b_evaluated_releases": cfr_b.evaluated_count,
        "cfr_b_failed_releases": cfr_b.failed_count,
        "cfr_b_censored_releases": cfr_b.censored_count,
        "recovery_median_hours": "" if not durations else statistics.median(durations),
        "recovery_censored_count": recoveries.censored_count,
        "eligible": "true",
        "exclusion_reason": "",
    }


def _bounded_history(
    client: GitHubClient,
    *,
    repository: str,
    default_branch: str,
    window: ObservationWindow,
) -> ReleaseHistory:
    """Releases da janela e o compare com a anterior. Nao baixa o historico inteiro."""

    history = ReleaseHistory(repository=repository, default_branch=default_branch)
    raw_releases: list[dict[str, Any]] = []
    window_start = window.start.isoformat()
    for page in range(1, 31):
        payload = client.get(f"/repos/{repository}/releases", {"per_page": 100, "page": page}).payload
        if not isinstance(payload, list) or not payload:
            break
        page_items = [item for item in payload if isinstance(item, dict)]
        raw_releases.extend(page_items)
        published = [str(item.get("published_at") or "") for item in page_items]
        published = [item for item in published if item]
        oldest = min(published) if published else ""
        if oldest and oldest < window_start:
            break
        if len(payload) < 100:
            break

    records = [
        normalize_release(item, repository=repository, default_branch=default_branch, window=window)
        for item in raw_releases
    ]
    primary_records = [record for record in records if record.primary]
    history.releases = [record.to_dict() for record in primary_records]
    if len(primary_records) > MAX_PRIMARY_RELEASES:
        return history
    compares: list[dict[str, Any]] = []
    pairs = list(pair_with_previous(records))

    def compare_one(pair: tuple[Any, Any]) -> dict[str, Any]:
        head, previous = pair
        if not head.tag_name or previous is None or not previous.tag_name:
            problem = "missing_tag" if not head.tag_name or (previous is not None and not previous.tag_name) else "no_previous_release"
            return {
                "repository": repository,
                "base_tag": "" if previous is None else previous.tag_name,
                "head_tag": head.tag_name,
                "commits": [],
                "problem": problem,
                "detail": problem,
                "skipped_missing_date": 0,
            }
        try:
            compare, _pages = collect_commits_between(client, repository, previous.tag_name, head.tag_name)
        except Exception as error:
            return {
                "repository": repository,
                "base_tag": previous.tag_name,
                "head_tag": head.tag_name,
                "commits": [],
                "problem": "compare_error",
                "detail": str(error),
                "skipped_missing_date": 0,
            }
        return compare.to_dict()

    with ThreadPoolExecutor(max_workers=6) as pool:
        compares.extend(pool.map(compare_one, pairs))
    history.compares = compares
    return history


def _search(client: GitHubClient, stars: str, page: int, extra: str = "") -> dict[str, Any]:
    query = f"stars:{stars} archived:false pushed:>=2025-01-01"
    if extra:
        query = f"{query} {extra}"
    response = client.get(
        "/search/repositories",
        {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 100,
            "page": page,
        },
    )
    payload = response.payload
    return payload if isinstance(payload, dict) else {}


def collect_until(client: GitHubClient, *, root: Path, target: int, window: ObservationWindow) -> dict[str, Any]:
    state = _load_state(root)
    seen = set(state["seen"])
    already_recorded = set(state["seen"])
    ranges: list[tuple[str, str]] = [
        ("1000..2000", ""),
        ("2001..5000", ""),
        ("5001..10000", ""),
        ("10001..50000", ""),
        ("50001..*", ""),
    ]
    used_language_wave = False
    runs_client = WorkflowRunClient(client.token or "", cache_dir=root / "cache" / "http")
    while state["funnel"]["eligible"] < target:
        if not ranges:
            if used_language_wave:
                break
            used_language_wave = True
            languages = (
                "language:Python",
                "language:TypeScript",
                "language:JavaScript",
                "language:Go",
                "language:Java",
                "language:Rust",
                "language:PHP",
                "language:Ruby",
                "language:C#",
                "language:Kotlin",
            )
            bands = ("200..500", "501..999", "1000..2000", "2001..5000", "5001..10000", "10001..50000", "50001..*")
            ranges = [(band, language) for language in languages for band in bands]
            print(f"faixas iniciais esgotadas com {state['funnel']['eligible']} elegiveis; abrindo busca por linguagem", flush=True)
            continue
        stars, extra = ranges.pop(0)
        time.sleep(2.1)
        try:
            first = _search(client, stars, 1, extra)
        except GitHubApiError as error:
            print(f"busca falhou {stars} {extra}: {error}", flush=True)
            state["funnel"]["errors"] += 1
            _save_state(root, state)
            continue
        total = int(first.get("total_count") or 0)
        print(f"faixa {stars} {extra} total={total} elegiveis={state['funnel']['eligible']}", flush=True)
        if total > 1000:
            pieces = split_star_range(stars)
            if pieces != [stars]:
                ranges[0:0] = [(piece, extra) for piece in pieces]
                continue
        items = list(first.get("items") or [])
        for page in range(2, 11):
            if len(items) >= total or len(items) >= 1000:
                break
            time.sleep(2.1)
            try:
                payload = _search(client, stars, page, extra)
            except GitHubApiError:
                break
            page_items = payload.get("items") or []
            if not page_items:
                break
            items.extend(page_items)
        for item in items:
            if state["funnel"]["eligible"] >= target:
                break
            repository = str(item.get("full_name") or "")
            branch = str(item.get("default_branch") or "")
            if not repository or not branch:
                continue
            if repository in seen:
                if repository not in already_recorded:
                    state["funnel"]["duplicates"] += 1
                continue
            seen.add(repository)
            state["seen"].append(repository)
            state["funnel"]["candidates"] += 1
            try:
                runs_total = _run_count(client, repository, branch)
                if runs_total >= 50:
                    state["funnel"]["with_workflow_runs"] += 1
                    if _has_minimum_releases(client, repository, branch, window):
                        state["funnel"]["with_releases"] += 1
                        print(f"medindo {repository}", flush=True)
                        history = _bounded_history(
                            client,
                            repository=repository,
                            default_branch=branch,
                            window=window,
                        )
                        if history.primary_count > MAX_PRIMARY_RELEASES:
                            state["funnel"]["release_cap_skipped"] = state["funnel"].get("release_cap_skipped", 0) + 1
                            print(
                                f"acima do teto {repository}: {history.primary_count} releases na janela",
                                flush=True,
                            )
                            _save_state(root, state)
                            continue
                        collected = _collect_runs_fast(
                            client,
                            repository,
                            branch,
                            window,
                            runs_client,
                            root / "data" / "raw" / "workflow_runs",
                        )
                        if history.primary_count >= 5 and len(collected.runs) >= 50:
                            state["eligible"].append(_metric_row(history, collected.runs, window))
                            state["funnel"]["eligible"] += 1
                            print(
                                f"elegivel {state['funnel']['eligible']}/{target}: {repository} "
                                f"releases={history.primary_count} runs={len(collected.runs)}",
                                flush=True,
                            )
            except Exception as error:
                state["funnel"]["errors"] += 1
                print(f"erro {repository}: {error}", flush=True)
            if state["funnel"]["candidates"] % 25 == 0 or (
                state["eligible"] and state["eligible"][-1]["repository"] == repository
            ):
                print(
                    f"triados {state['funnel']['candidates']} "
                    f"runs>={50}:{state['funnel']['with_workflow_runs']} "
                    f"elegiveis={state['funnel']['eligible']}",
                    flush=True,
                )
                _save_state(root, state)
    _save_state(root, state)
    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coleta a amostra final de 300 repositorios elegiveis.")
    parser.add_argument("--lab-root", type=Path, default=LAB3_ROOT)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--target", type=int, default=TARGET_ELIGIBLE)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.lab_root
    config_path = args.config or (root / "config" / "lab3s02.json")
    config = load_config(config_path)
    window = ObservationWindow.from_config(config)
    client = GitHubClient.from_environment(cache_dir=root / "cache" / "http")
    state = collect_until(client, root=root, target=args.target, window=window)
    print(
        f"Amostra final: {state['funnel']['eligible']} elegiveis de {state['funnel']['candidates']} candidatos.",
        flush=True,
    )
    return 0 if state["funnel"]["eligible"] >= args.target else 1


if __name__ == "__main__":
    raise SystemExit(main())
