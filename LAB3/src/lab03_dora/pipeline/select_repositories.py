"""Command line entry point for LAB3S01 issues #95 and #96."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from lab03_dora.api.github import GitHubClient
from lab03_dora.collection.repositories import (
    attach_actions_metadata,
    deduplicate_candidates,
    normalize_repository,
)
from lab03_dora.collection.selection import (
    SelectionCriteria,
    build_funnel,
    build_selection_table,
    read_csv,
    write_csv,
)


LAB3_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = LAB3_ROOT / "config" / "lab3s01.json"
DEFAULT_CANDIDATES_CSV = LAB3_ROOT / "data" / "interim" / "selection" / "candidate_repositories.csv"
DEFAULT_SELECTED_CSV = LAB3_ROOT / "data" / "interim" / "selection" / "s01_repository_selection.csv"
DEFAULT_FUNNEL_CSV = LAB3_ROOT / "reports" / "funnel" / "s01_selection_funnel.csv"


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def collect_candidates(config: dict, *, limit: int | None = None, target_with_actions: int = 100) -> list[dict]:
    client = GitHubClient.from_environment()
    search_config = config.get("repository_search", {})
    repositories = []
    for stars in search_config.get("star_ranges", ["1000..*"]):
        repositories.extend(
            normalize_repository(item)
            for item in client.search_repositories(
                stars=stars,
                sort=search_config.get("sort", "stars"),
                order=search_config.get("order", "desc"),
                per_page=int(search_config.get("per_page", 100)),
            )
        )
        if limit is not None and len(repositories) >= limit:
            break

    enriched = []
    with_actions_count = 0
    for candidate in deduplicate_candidates(repositories):
        if limit is not None and len(enriched) >= limit:
            break
        workflows = client.repository_workflows(candidate.full_name)
        enriched_candidate = attach_actions_metadata(candidate, workflows).to_row()
        enriched.append(enriched_candidate)
        if enriched_candidate["has_actions"]:
            with_actions_count += 1
        if with_actions_count >= target_with_actions:
            break
    return enriched


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seleciona candidatos e gera o funil da LAB3S01."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--input-csv", type=Path, help="CSV de candidatos ja coletados; evita chamada a API.")
    parser.add_argument("--candidates-out", type=Path, default=DEFAULT_CANDIDATES_CSV)
    parser.add_argument("--selection-out", type=Path, default=DEFAULT_SELECTED_CSV)
    parser.add_argument("--funnel-out", type=Path, default=DEFAULT_FUNNEL_CSV)
    parser.add_argument("--limit", type=int, default=None, help="Limite opcional de candidatos verificados para smoke test.")
    parser.add_argument(
        "--target-with-actions",
        type=int,
        default=None,
        help="Quantidade alvo de repositorios com GitHub Actions antes de parar a coleta.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    selection_config = config.get("selection", {})
    criteria = SelectionCriteria(
        target_s01_sample_size=int(selection_config.get("target_s01_sample_size", 100)),
        minimum_releases=int(selection_config.get("minimum_releases", 5)),
        minimum_valid_workflow_runs=int(selection_config.get("minimum_valid_workflow_runs", 50)),
    )

    if args.input_csv:
        candidates = read_csv(args.input_csv)
    else:
        target_with_actions = args.target_with_actions or criteria.target_s01_sample_size
        candidates = collect_candidates(config, limit=args.limit, target_with_actions=target_with_actions)
        write_csv(args.candidates_out, candidates)

    selection_rows = build_selection_table(candidates, criteria)
    funnel_rows = build_funnel(selection_rows, criteria)

    write_csv(args.selection_out, selection_rows)
    write_csv(args.funnel_out, funnel_rows, fieldnames=("stage", "count", "discarded", "description"))

    selected_count = sum(1 for row in selection_rows if row["selection_status"] == "eligible_s01")
    base_sample_count = sum(1 for row in selection_rows if row["selection_status"] == "s01_base_sample")
    pending_count = sum(1 for row in selection_rows if row["selection_status"] == "pending_downstream_collection")
    print(
        f"Selecao LAB3S01: {len(selection_rows)} candidatos, "
        f"{base_sample_count} na base S01, {selected_count} elegiveis finais, {pending_count} pendentes"
    )
    print(f"Selecao: {args.selection_out}")
    print(f"Funil: {args.funnel_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
