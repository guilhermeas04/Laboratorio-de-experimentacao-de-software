"""Coleta PRs reais para o cenário P1 do LAB4."""

from __future__ import annotations

import argparse
import csv
import json
import os
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPOSITORIES = ROOT.parent / "LAB3" / "data" / "processed" / "datasets" / "s02_metrics.csv"
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "pr_merge_time.csv"
DEFAULT_METADATA = ROOT / "data" / "raw" / "collection_metadata.json"
OBSERVATIONS_PER_GROUP = 30
API_ROOT = "https://api.github.com"


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def bot_group(pull_request: dict[str, Any]) -> str:
    user = pull_request.get("user") or {}
    login = str(user.get("login") or "").lower()
    return "bot" if user.get("type") == "Bot" or login.endswith("[bot]") else "human"


def duration_hours(pull_request: dict[str, Any]) -> float | None:
    created = pull_request.get("created_at")
    merged = pull_request.get("merged_at")
    if not created or not merged:
        return None
    duration = (parse_timestamp(str(merged)) - parse_timestamp(str(created))).total_seconds() / 3600
    return duration if duration >= 0 else None


def github_get(path: str, token: str | None) -> tuple[Any, dict[str, str]]:
    request = urllib.request.Request(
        API_ROOT + path,
        headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response), dict(response.headers.items())


def collect(repositories: Iterable[str], token: str | None, limit: int = OBSERVATIONS_PER_GROUP) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for repository in repositories:
        if _complete(observations, limit):
            break
        page = 1
        while page <= 3 and not _complete(observations, limit):
            query = urllib.parse.urlencode({"state": "closed", "sort": "updated", "direction": "desc", "per_page": 100, "page": page})
            try:
                payload, _ = github_get(f"/repos/{repository}/pulls?{query}", token)
            except urllib.error.HTTPError as error:
                if error.code != 401 or not token:
                    raise
                payload, _ = github_get(f"/repos/{repository}/pulls?{query}", None)
            if not isinstance(payload, list) or not payload:
                break
            for pull_request in payload:
                if not isinstance(pull_request, dict) or not pull_request.get("merged_at"):
                    continue
                group = bot_group(pull_request)
                if _count(observations, group) >= limit:
                    continue
                hours = duration_hours(pull_request)
                if hours is None:
                    continue
                observations.append({
                    "repository": repository,
                    "pull_request_number": pull_request.get("number"),
                    "group": group,
                    "duration_hours": round(hours, 6),
                    "created_at": pull_request.get("created_at"),
                    "merged_at": pull_request.get("merged_at"),
                    "author_login": (pull_request.get("user") or {}).get("login", ""),
                    "author_type": (pull_request.get("user") or {}).get("type", ""),
                    "source_url": pull_request.get("html_url", ""),
                })
            page += 1
        if _complete(observations, limit):
            break
    if not _complete(observations, limit):
        raise RuntimeError(f"coleta insuficiente: bot={_count(observations, 'bot')}, human={_count(observations, 'human')}")
    return [row for group in ("bot", "human") for row in observations if row["group"] == group][: limit * 2]


def _count(rows: list[dict[str, Any]], group: str) -> int:
    return sum(row["group"] == group for row in rows)


def _complete(rows: list[dict[str, Any]], limit: int) -> bool:
    return _count(rows, "bot") >= limit and _count(rows, "human") >= limit


def read_repositories(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row["repository"] for row in csv.DictReader(handle) if row.get("repository")]


def write_outputs(rows: list[dict[str, Any]], output: Path, metadata_path: Path, source: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "scenario": "P1: tempo ate o merge de PRs de autoria de bot versus autoria humana",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "GitHub REST API GET /repos/{owner}/{repo}/pulls?state=closed&sort=updated",
        "authentication": "token when accepted; anonymous fallback on HTTP 401",
        "source_repository_list": source.relative_to(ROOT.parent).as_posix() if source.resolve().is_relative_to(ROOT.parent.resolve()) else source.name,
        "groups": {"bot": OBSERVATIONS_PER_GROUP, "human": OBSERVATIONS_PER_GROUP},
        "unit": "hours between pull request created_at and merged_at",
        "inclusion": ["public repository in S02 dataset", "closed pull request with merged_at", "valid non-negative created_at to merged_at duration", "author classified as bot or human"],
        "exclusion": ["unmerged pull requests", "missing timestamps", "negative durations", "observations after the first 30 per group"],
        "bot_rule": "user.type == Bot or login ends with [bot]; all other authors are human",
        "limitations": ["GitHub author metadata is an operational proxy for automation", "sample is convenience-based and limited to repositories reachable during collection", "only recent closed PR pages were inspected"],
        "raw_file": output.relative_to(ROOT).as_posix(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta 30 PRs bot e 30 PRs humanos.")
    parser.add_argument("--repositories", type=Path, default=DEFAULT_REPOSITORIES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--force", action="store_true", help="permite substituir os arquivos de saída existentes")
    args = parser.parse_args()
    if not args.force:
        existing = [path for path in (args.output, args.metadata) if path.exists()]
        if existing:
            names = ", ".join(str(path) for path in existing)
            raise FileExistsError(f"saídas já existentes: {names}; use --force para substituir")
    token = os.environ.get("GITHUB_TOKEN")
    rows = collect(read_repositories(args.repositories), token)
    write_outputs(rows, args.output, args.metadata, args.repositories)
    print(f"Coletadas {len(rows)} observacoes: bot={_count(rows, 'bot')}, human={_count(rows, 'human')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())