"""Metadados dos 300 repositorios para os subgrupos da RQ06.

Linguagem, estrelas, idade e contribuidores vem de `GET /repos/{repo}` e de
`GET /repos/{repo}/contributors?per_page=1&anon=true`, lendo o numero da
ultima pagina no cabecalho Link.
"""

from __future__ import annotations

import argparse
import csv
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Sequence

from lab03_dora.api.github import GitHubApiError, GitHubClient

LAB3_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = LAB3_ROOT / "data" / "processed" / "datasets" / "s02_metrics.csv"
DEFAULT_OUTPUT = LAB3_ROOT / "data" / "processed" / "datasets" / "s02_repository_metadata.csv"
WINDOW_END = date(2025, 12, 31)
COLUMNS = (
    "repository",
    "language",
    "stars",
    "forks",
    "created_at",
    "age_years",
    "contributors",
    "collected_at",
    "problem",
)
LAST_PAGE = re.compile(r"[?&]page=(\d+)[^>]*>;\s*rel=\"last\"")


def contributor_count(payload: Any, link_header: str) -> int:
    """Com per_page=1, o numero da ultima pagina e o total de contribuidores."""

    match = LAST_PAGE.search(link_header or "")
    if match:
        return int(match.group(1))
    return len(payload) if isinstance(payload, list) else 0


def age_in_years(created_at: str, reference: date = WINDOW_END) -> float | None:
    if not created_at:
        return None
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
    return (reference - created).days / 365.25


def metadata_row(repository: str, payload: dict[str, Any], contributors: int | None, collected_at: str, problem: str = "") -> dict[str, Any]:
    created_at = str(payload.get("created_at") or "")
    age = age_in_years(created_at)
    return {
        "repository": repository,
        "language": str(payload.get("language") or ""),
        "stars": payload.get("stargazers_count", ""),
        "forks": payload.get("forks_count", ""),
        "created_at": created_at,
        "age_years": "" if age is None else round(age, 4),
        "contributors": "" if contributors is None else contributors,
        "collected_at": collected_at,
        "problem": problem,
    }


def collect_one(client: GitHubClient, repository: str, collected_at: str) -> dict[str, Any]:
    try:
        repo = client._request_json(client._build_url(f"/repos/{repository}")).payload
    except Exception as error:
        return {**{column: "" for column in COLUMNS}, "repository": repository, "collected_at": collected_at, "problem": f"repo_request_failed: {error}"}
    if not isinstance(repo, dict):
        return {**{column: "" for column in COLUMNS}, "repository": repository, "collected_at": collected_at, "problem": "repo_payload_invalid"}
    try:
        response = client._request_json(
            client._build_url(f"/repos/{repository}/contributors", {"per_page": 1, "anon": "true"})
        )
        contributors: int | None = contributor_count(response.payload, response.headers.get("link", ""))
        problem = ""
    except Exception as error:
        # A API recusa a lista de contribuidores de historicos muito grandes.
        contributors, problem = None, f"contributors_unavailable: {error}"
    return metadata_row(repository, repo, contributors, collected_at, problem)


def read_repositories(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row["repository"] for row in csv.DictReader(handle) if row.get("repository")]


def write_rows(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coleta linguagem, estrelas, idade e contribuidores dos repositorios do dataset S02.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=6)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = GitHubClient.from_environment(cache_dir=None)
    repositories = read_repositories(args.input)
    collected_at = datetime.now(UTC).isoformat(timespec="seconds")
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(lambda repository: collect_one(client, repository, collected_at), repositories))
    write_rows(args.output, rows)
    problems = sum(1 for row in rows if row["problem"])
    print(f"Metadados: {len(rows)} repositorios, {problems} com problema; saida em {args.output}")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
