"""Coleta a variante de deployment por tags para a RQ07.

Tags anotadas são convertidas em uma contagem dentro da janela de 2025. Cada
resposta REST é cacheada pelo cliente e o CSV de saída é atualizado por repo,
permitindo interromper e retomar a execução.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path


START = "2025-01-01T00:00:00+00:00"
END = "2025-12-31T23:59:59+00:00"


GH = r"C:\Program Files\GitHub CLI\gh.exe"

def gh_api(path: str) -> object:
    environment = dict(__import__("os").environ)
    environment.pop("GITHUB_TOKEN", None)
    result = subprocess.run([GH, "api", path], check=True, capture_output=True, text=True, encoding="utf-8", env=environment)
    return json.loads(result.stdout)


def collect_graphql(repository: str) -> dict[str, str]:
    owner, name = repository.split("/", 1)
    query = """query($owner:String!, $name:String!) { repository(owner:$owner,name:$name) { refs(refPrefix:\"refs/tags/\", first:100) { nodes { name target { __typename ... on Commit { authoredDate } ... on Tag { target { __typename ... on Commit { authoredDate } } } } } } } }"""
    environment = dict(__import__("os").environ); environment.pop("GITHUB_TOKEN", None)
    result = subprocess.run([GH, "api", "graphql", "-f", f"query={query}", "-F", f"owner={owner}", "-F", f"name={name}"], check=True, capture_output=True, text=True, encoding="utf-8", env=environment)
    data = json.loads(result.stdout)
    nodes = (((data.get("data") or {}).get("repository") or {}).get("refs") or {}).get("nodes") or []
    if not nodes:
        raise ValueError(f"GraphQL nao retornou tags para {repository}")
    def date(node):
        target = node.get("target") or {}
        return target.get("authoredDate") or ((target.get("target") or {}).get("authoredDate") or "")
    count = sum(1 for node in nodes if START <= str(date(node)) <= END)
    return {"repository": repository, "tag_count": str(count), "tag_deployment_frequency_per_week": str(count / (365 / 7))}


def collect_one(repository: str) -> dict[str, str]:
    tags = []
    for page in range(1, 31):
        payload = gh_api(f"repos/{repository}/tags?per_page=100&page={page}")
        if not isinstance(payload, list) or not payload:
            break
        for tag in payload:
            if not isinstance(tag, dict):
                continue
            sha = str((tag.get("commit") or {}).get("sha") or "")
            if not sha:
                continue
            commit = gh_api(f"repos/{repository}/commits/{sha}")
            authored = str(((commit or {}).get("commit") or {}).get("author", {}).get("date") or "")
            if START <= authored <= END:
                tags.append(sha)
        if len(payload) < 100:
            break
    return {"repository": repository, "tag_count": str(len(set(tags))), "tag_deployment_frequency_per_week": str(len(set(tags)) / (365 / 7))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/processed/datasets/s02_metrics.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/datasets/rq07_tags.csv"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    existing = {}
    if args.output.exists():
        with args.output.open(encoding="utf-8", newline="") as handle:
            existing = {row["repository"]: row for row in csv.DictReader(handle)}
    pending = [row["repository"] for row in rows if row["repository"] not in existing]
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for result in pool.map(collect_one, pending):
            existing[result["repository"]] = result
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=("repository", "tag_count", "tag_deployment_frequency_per_week"))
                writer.writeheader(); writer.writerows(existing.values())
            print(f"tags {len(existing)}/{len(rows)} {result['repository']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
