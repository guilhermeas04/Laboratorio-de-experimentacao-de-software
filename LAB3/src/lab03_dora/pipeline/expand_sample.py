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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
                "low_runs": 0,
                "low_releases": 0,
                "measured_not_eligible": 0,
                "release_cap_skipped": 0,
            },
        }
    state = json.loads(path.read_text(encoding="utf-8"))
    funnel = state["funnel"]
    if "low_runs" not in funnel:
        funnel["low_runs"] = funnel["candidates"] - funnel["with_workflow_runs"]
        funnel["low_releases"] = funnel["with_workflow_runs"] - funnel["with_releases"]
        funnel["measured_not_eligible"] = max(
            0, funnel["with_releases"] - funnel["eligible"] - funnel.get("release_cap_skipped", 0)
        )
    accounted = sum(
        int(funnel.get(key) or 0)
        for key in ("low_runs", "low_releases", "release_cap_skipped", "measured_not_eligible", "errors", "eligible", "interrupted")
    )
    if funnel["candidates"] > accounted:
        funnel["interrupted"] = int(funnel.get("interrupted") or 0) + funnel["candidates"] - accounted
    return state


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
            {"stage": "candidates", "count": counts["candidates"], "discarded": 0, "description": "Repositorios distintos retornados pela busca, nao arquivados, com push em 2025."},
            {"stage": "excluded_low_releases", "count": counts.get("low_releases", 0), "discarded": counts.get("low_releases", 0), "description": "Menos de 5 releases primarias dentro da janela."},
            {"stage": "excluded_low_workflow_runs", "count": counts.get("low_runs", 0), "discarded": counts.get("low_runs", 0), "description": "Menos de 50 workflow runs de push concluidos no default branch, dentro da janela."},
            {"stage": "release_cap_skipped", "count": counts.get("release_cap_skipped", 0), "discarded": counts.get("release_cap_skipped", 0), "description": "Mais de 60 releases primarias na janela. O compare de cada release estoura a cota da API, entao o repositorio fica fora da amostra."},
            {"stage": "measured_not_eligible", "count": counts.get("measured_not_eligible", 0), "discarded": counts.get("measured_not_eligible", 0), "description": "Passou na triagem, mas a medicao completa nao confirmou 5 releases primarias no default branch e 50 runs validos."},
            {"stage": "errors", "count": counts["errors"], "discarded": counts["errors"], "description": "Consulta falhou; o repositorio nao entrou na amostra."},
            {"stage": "interrupted", "count": counts.get("interrupted", 0), "discarded": counts.get("interrupted", 0), "description": "Retornado pela busca, mas nao medido: a coleta foi reiniciada no meio do lote ou o alvo de 300 ja tinha sido atingido."},
            {"stage": "eligible_final", "count": counts["eligible"], "discarded": 0, "description": "Amostra final, sem repositorio duplicado."},
            {"stage": "duplicates_ignored", "count": counts["duplicates"], "discarded": counts["duplicates"], "description": "Repositorio devolvido de novo por outra busca; so a primeira ocorrencia conta."},
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
    at_limit = total >= 1000
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
        if page >= 10 or page * 100 >= total or not runs_in_page or len(runs_in_page) < 100:
            break
        page += 1
        payload = client.get(f"/repos/{repository}/actions/runs", {**params, "page": page}).payload
    return CollectionResult(runs=collected, windows_at_limit=["2025"] if at_limit else [])


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
            compare, _pages = collect_commits_between(
                client, repository, previous.tag_name, head.tag_name, max_pages=1
            )
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

    graphql_results = _graphql_compares(client.token or "", repository, pairs)

    def resolve(pair: tuple[Any, Any]) -> dict[str, Any]:
        head, previous = pair
        if head.tag_name and previous is not None and previous.tag_name:
            cached = graphql_results.get((previous.tag_name, head.tag_name))
            if cached is not None:
                return cached
        return compare_one(pair)

    with ThreadPoolExecutor(max_workers=6) as pool:
        compares.extend(pool.map(resolve, pairs))
    history.compares = compares
    return history


def _graphql_compares(token: str, repository: str, pairs: list[tuple[Any, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Commits entre releases pela API GraphQL, 10 compares por consulta.

    Mesma regra do compare REST: commits do head que nao estao no base, os
    100 mais antigos primeiro. Compare que falhar volta como ausente e cai no
    REST.
    """

    owner, name = repository.split("/", 1)
    wanted = [
        (previous.tag_name, head.tag_name)
        for head, previous in pairs
        if head.tag_name and previous is not None and previous.tag_name
    ]
    results: dict[tuple[str, str], dict[str, Any]] = {}
    for start in range(0, len(wanted), 10):
        chunk = wanted[start : start + 10]
        parts = []
        for index, (base_tag, head_tag) in enumerate(chunk):
            parts.append(
                f"c{index}: ref(qualifiedName: {json.dumps('refs/tags/' + base_tag)}) {{"
                f" compare(headRef: {json.dumps('refs/tags/' + head_tag)}) {{"
                " aheadBy commits(first: 100) { pageInfo { hasNextPage endCursor } nodes { oid authoredDate message } } } }"
            )
        query = f"query {{ repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ {' '.join(parts)} }} }}"
        try:
            data = _graphql(token, query, {})
        except GitHubApiError:
            continue
        repo_data = data.get("repository") or {}
        for index, (base_tag, head_tag) in enumerate(chunk):
            ref = repo_data.get(f"c{index}")
            comparison = (ref or {}).get("compare")
            if not comparison:
                continue
            connection = comparison.get("commits") or {}
            nodes = list(connection.get("nodes") or [])
            page_info = connection.get("pageInfo") or {}
            pages = 1
            while page_info.get("hasNextPage") and pages < 20:
                follow = (
                    f"query($after: String) {{ repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{"
                    f" ref(qualifiedName: {json.dumps('refs/tags/' + base_tag)}) {{"
                    f" compare(headRef: {json.dumps('refs/tags/' + head_tag)}) {{"
                    " commits(first: 100, after: $after) { pageInfo { hasNextPage endCursor } nodes { oid authoredDate message } } } } } }"
                )
                try:
                    more = _graphql(token, follow, {"after": page_info.get("endCursor")})
                    more_connection = (((more.get("repository") or {}).get("ref") or {}).get("compare") or {}).get("commits") or {}
                except GitHubApiError:
                    break
                nodes.extend(more_connection.get("nodes") or [])
                page_info = more_connection.get("pageInfo") or {}
                pages += 1
            commits = []
            skipped = 0
            for node in nodes:
                sha = str((node or {}).get("oid") or "")
                authored = str((node or {}).get("authoredDate") or "")
                if not sha or not authored:
                    skipped += 1
                    continue
                lines = str(node.get("message") or "").splitlines()
                commits.append({"sha": sha, "authored_at": authored, "message": lines[0] if lines else ""})
            ahead = int(comparison.get("aheadBy") or 0)
            problem, detail = "", ""
            if ahead > len(nodes):
                problem = "compare_truncated"
                detail = f"A API informou {ahead} commits, mas {len(nodes)} foram recebidos."
            elif not commits:
                problem = "no_new_commits"
                detail = "O compare nao trouxe commits novos com data de autor."
            elif skipped:
                problem = "missing_commit_date"
                detail = f"{skipped} commit(s) sem sha ou data de autor foram ignorados."
            results[(base_tag, head_tag)] = {
                "repository": repository,
                "base_tag": base_tag,
                "head_tag": head_tag,
                "commits": commits,
                "problem": problem,
                "detail": detail,
                "skipped_missing_date": skipped,
            }
    return results


GRAPHQL_SEARCH = """
query($q: String!, $after: String) {
  rateLimit { remaining resetAt }
  search(query: $q, type: REPOSITORY, first: 50, after: $after) {
    repositoryCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on Repository {
        nameWithOwner
        defaultBranchRef { name }
        releases(first: 50, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes { publishedAt isDraft isPrerelease }
        }
      }
    }
  }
}
"""


def _graphql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(6):
        request = Request(
            "https://api.github.com/graphql",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "lab03-dora-pipeline",
            },
        )
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            last_error = error
            if error.code in (403, 429):
                reset = error.headers.get("X-RateLimit-Reset")
                wait = max(5, int(reset) - int(time.time()) + 1) if reset and reset.isdigit() else 60
                print(f"cota GraphQL, esperando {wait}s", flush=True)
                time.sleep(wait)
                continue
            if error.code >= 500:
                time.sleep(2**attempt)
                continue
            raise GitHubApiError(f"GraphQL retornou HTTP {error.code}") from error
        except (URLError, OSError) as error:
            last_error = error
            time.sleep(2**attempt)
            continue
        if payload.get("errors") and not payload.get("data"):
            last_error = GitHubApiError(str(payload["errors"])[:300])
            time.sleep(2**attempt)
            continue
        return payload.get("data") or {}
    raise GitHubApiError(f"GraphQL falhou: {last_error}")


def _release_hint(node: dict[str, Any], window: ObservationWindow) -> bool:
    """Pre-filtro barato. A contagem oficial sai depois da API REST."""

    releases = ((node.get("releases") or {}).get("nodes")) or []
    start = window.start.isoformat()
    end = window.end.isoformat() + "T23:59:59Z"
    in_window = 0
    newest_after_window = 0
    for release in releases:
        published = str(release.get("publishedAt") or "")
        if not published or release.get("isDraft") or release.get("isPrerelease"):
            continue
        if published > end:
            newest_after_window += 1
        elif published >= start:
            in_window += 1
    if in_window >= 5:
        return True
    return len(releases) >= 50 and in_window + newest_after_window >= len(releases) - 5


def _search_params(stars: str, page: int, extra: str) -> dict[str, Any]:
    query = f"stars:{stars} archived:false pushed:>=2025-01-01"
    if extra:
        query = f"{query} {extra}"
    return {"q": query, "sort": "stars", "order": "desc", "per_page": 100, "page": page}


def _throttle_search(client: GitHubClient, stars: str, page: int, extra: str) -> None:
    """A busca do GitHub aceita 30 pedidos por minuto. Cache nao conta."""

    url = client._build_url("/search/repositories", _search_params(stars, page, extra))
    cache_path = client._cache_path(url)
    if cache_path is None or not cache_path.exists():
        time.sleep(2.1)


def _search(client: GitHubClient, stars: str, page: int, extra: str = "") -> dict[str, Any]:
    response = client.get("/search/repositories", _search_params(stars, page, extra))
    payload = response.payload
    return payload if isinstance(payload, dict) else {}


def collect_until(client: GitHubClient, *, root: Path, target: int, window: ObservationWindow) -> dict[str, Any]:
    state = _load_state(root)
    seen = set(state["seen"])
    already_recorded = set(state["seen"])
    done_ranges = set(state.get("done_ranges") or [])
    token = client.token or ""
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
        range_key = f"{stars}|{extra}"
        if range_key in done_ranges:
            continue
        query = f"stars:{stars} archived:false pushed:>=2025-01-01 sort:stars-desc"
        if extra:
            query = f"{query} {extra}"
        try:
            first = _graphql(token, GRAPHQL_SEARCH, {"q": query, "after": None})["search"]
        except (GitHubApiError, KeyError, TypeError) as error:
            print(f"busca falhou {stars} {extra}: {error}", flush=True)
            state["funnel"]["errors"] += 1
            _save_state(root, state)
            continue
        total = int(first.get("repositoryCount") or 0)
        print(f"faixa {stars} {extra} total={total} elegiveis={state['funnel']['eligible']}", flush=True)
        if total > 1000:
            pieces = split_star_range(stars)
            if pieces != [stars]:
                ranges[0:0] = [(piece, extra) for piece in pieces]
                continue
        nodes = list(first.get("nodes") or [])
        page_info = first.get("pageInfo") or {}
        while page_info.get("hasNextPage") and len(nodes) < 1000:
            time.sleep(0.5)
            try:
                page = _graphql(token, GRAPHQL_SEARCH, {"q": query, "after": page_info.get("endCursor")})["search"]
            except (GitHubApiError, KeyError, TypeError):
                break
            nodes.extend(page.get("nodes") or [])
            page_info = page.get("pageInfo") or {}
        fresh: list[tuple[str, str, bool]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            repository = str(node.get("nameWithOwner") or "")
            branch = str((node.get("defaultBranchRef") or {}).get("name") or "")
            if not repository or not branch:
                continue
            if repository in seen:
                if repository not in already_recorded:
                    state["funnel"]["duplicates"] += 1
                continue
            seen.add(repository)
            state["seen"].append(repository)
            state["funnel"]["candidates"] += 1
            fresh.append((repository, branch, _release_hint(node, window)))

        def screen_one(item: tuple[str, str, bool]) -> tuple[str, str, str]:
            repository, branch, hint = item
            if not hint:
                return repository, branch, "low_releases"
            try:
                if _run_count(client, repository, branch) < 50:
                    return repository, branch, "low_runs"
                return repository, branch, "measure"
            except Exception as error:
                print(f"erro {repository}: {error}", flush=True)
                return repository, branch, "error"

        screened: list[tuple[str, str, str]] = []
        if fresh:
            with ThreadPoolExecutor(max_workers=8) as pool:
                screened = list(pool.map(screen_one, fresh))
        for repository, branch, status in screened:
            if state["funnel"]["eligible"] >= target:
                break
            if status == "error":
                state["funnel"]["errors"] += 1
                continue
            if status == "low_runs":
                state["funnel"]["low_runs"] += 1
                continue
            if status == "low_releases":
                state["funnel"]["low_releases"] += 1
                continue
            state["funnel"]["with_workflow_runs"] += 1
            state["funnel"]["with_releases"] += 1
            print(f"medindo {repository}", flush=True)
            try:
                history = _bounded_history(
                    client,
                    repository=repository,
                    default_branch=branch,
                    window=window,
                )
                if history.primary_count < 5:
                    state["funnel"]["low_releases"] += 1
                    continue
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
                    _save_state(root, state)
                elif len(collected.runs) < 50:
                    state["funnel"]["low_runs"] += 1
                else:
                    state["funnel"]["measured_not_eligible"] += 1
            except Exception as error:
                state["funnel"]["errors"] += 1
                print(f"erro {repository}: {error}", flush=True)
        if state["funnel"]["eligible"] < target:
            done_ranges.add(range_key)
            state["done_ranges"] = sorted(done_ranges)
        print(
            f"triados {state['funnel']['candidates']} "
            f"novos={len(fresh)} elegiveis={state['funnel']['eligible']}",
            flush=True,
        )
        _save_state(root, state)
    funnel = state["funnel"]
    accounted = sum(
        int(funnel.get(key) or 0)
        for key in ("low_runs", "low_releases", "release_cap_skipped", "measured_not_eligible", "errors", "eligible", "interrupted")
    )
    if funnel["candidates"] > accounted:
        funnel["interrupted"] = int(funnel.get("interrupted") or 0) + funnel["candidates"] - accounted
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
