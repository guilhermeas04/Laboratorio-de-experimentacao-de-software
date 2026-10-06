"""Coleta releases, tags e commits entre releases de um repositorio."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from lab03_dora.api.github import GitHubApiError, GitHubClient
from lab03_dora.collection.commits import collect_commits_between
from lab03_dora.collection.observation import ObservationWindow
from lab03_dora.collection.releases import normalize_release, pair_with_previous
from lab03_dora.collection.storage import repository_slug, write_json
from lab03_dora.collection.tags import GitHubReader, collect_tags


LAB3_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = LAB3_ROOT / "config" / "lab3s01.json"


@dataclass
class ReleaseHistory:
    repository: str
    default_branch: str
    releases: list[dict[str, Any]] = field(default_factory=list)
    tags: list[dict[str, Any]] = field(default_factory=list)
    compares: list[dict[str, Any]] = field(default_factory=list)
    problems: list[dict[str, Any]] = field(default_factory=list)

    @property
    def primary_count(self) -> int:
        return sum(1 for release in self.releases if release.get("primary"))


def collect_release_history(
    client: GitHubReader,
    *,
    repository: str,
    default_branch: str,
    window: ObservationWindow,
    lab_root: Path,
    compare_per_page: int = 250,
) -> ReleaseHistory:
    """Coleta um repositorio e grava cache bruto e saidas intermediarias.

    Falha de releases, tags ou compare fica registrada em problems. O restante
    da coleta desse repositorio, e dos proximos, continua.
    """

    history = ReleaseHistory(repository=repository, default_branch=default_branch)
    slug = repository_slug(repository)
    cache_dir = lab_root / "cache" / "api" / slug

    raw_releases: list[Any] = []
    try:
        raw_releases = list(client.paginate(f"/repos/{repository}/releases", {"per_page": 100}))
        write_json(cache_dir / "releases.json", raw_releases)
    except GitHubApiError as error:
        history.problems.append(_problem(repository, "releases_request_failed", repository, str(error)))

    release_records = []
    for payload in raw_releases:
        if not isinstance(payload, dict):
            history.problems.append(_problem(repository, "invalid_release_payload", repository, "Item ignorado."))
            continue
        record = normalize_release(
            payload,
            repository=repository,
            default_branch=default_branch,
            window=window,
        )
        release_records.append(record)
        if record.exclusion_reason:
            history.problems.append(
                _problem(repository, record.exclusion_reason, record.tag_name or record.release_id, record.exclusion_reason)
            )
        elif record.warning and record.warning != "missing_tag":
            history.problems.append(
                _problem(repository, record.warning, record.tag_name or record.release_id, record.warning)
            )

    try:
        tag_records, raw_tags = collect_tags(client, repository)
        write_json(cache_dir / "tags.json", raw_tags)
        history.tags = [record.to_dict() for record in tag_records]
        for record in tag_records:
            if record.problem:
                history.problems.append(_problem(repository, record.problem, record.name, record.detail))
    except GitHubApiError as error:
        history.problems.append(_problem(repository, "tags_request_failed", repository, str(error)))

    for head, previous in pair_with_previous(release_records):
        if not head.tag_name:
            history.compares.append(_empty_compare(repository, "", head.tag_name, "missing_tag", "A release primaria nao tem tag_name."))
            history.problems.append(_problem(repository, "missing_tag", head.release_id, "A release primaria nao tem tag_name."))
            continue
        if previous is None:
            history.compares.append(
                _empty_compare(repository, "", head.tag_name, "no_previous_release", "Primeira release publicada do default branch.")
            )
            history.problems.append(
                _problem(repository, "no_previous_release", head.tag_name, "Primeira release publicada do default branch.")
            )
            continue
        if not previous.tag_name:
            history.compares.append(
                _empty_compare(repository, "", head.tag_name, "missing_tag", "A release anterior nao tem tag_name.")
            )
            history.problems.append(_problem(repository, "missing_tag", head.tag_name, "A release anterior nao tem tag_name."))
            continue
        compare, raw_pages = collect_commits_between(
            client,
            repository,
            previous.tag_name,
            head.tag_name,
            per_page=compare_per_page,
        )
        write_json(cache_dir / f"compare-{_file_token(previous.tag_name)}-{_file_token(head.tag_name)}.json", raw_pages)
        history.compares.append(compare.to_dict())
        if compare.problem:
            history.problems.append(_problem(repository, compare.problem, head.tag_name, compare.detail))

    history.releases = [record.to_dict() for record in release_records]
    write_json(lab_root / "data" / "raw" / "github" / "releases" / f"{slug}.json", history.releases)
    write_json(lab_root / "data" / "raw" / "github" / "tags" / f"{slug}.json", history.tags)
    write_json(lab_root / "data" / "raw" / "github" / "commits" / f"{slug}.json", history.compares)
    write_json(lab_root / "data" / "interim" / "release_history" / f"{slug}.json", history.problems)
    return history


def collect_many(
    client: GitHubReader,
    repositories: Sequence[tuple[str, str]],
    *,
    window: ObservationWindow,
    lab_root: Path,
) -> list[ReleaseHistory]:
    """Coleta varios repositorios. A falha de um nao interrompe os demais."""

    histories: list[ReleaseHistory] = []
    for repository, default_branch in repositories:
        try:
            histories.append(
                collect_release_history(
                    client,
                    repository=repository,
                    default_branch=default_branch,
                    window=window,
                    lab_root=lab_root,
                )
            )
        except GitHubApiError as error:
            failed = ReleaseHistory(repository=repository, default_branch=default_branch)
            failed.problems.append(_problem(repository, "repository_collection_failed", repository, str(error)))
            histories.append(failed)
    return histories


def _empty_compare(repository: str, base_tag: str, head_tag: str, problem: str, detail: str) -> dict[str, Any]:
    return {
        "repository": repository,
        "base_tag": base_tag,
        "head_tag": head_tag,
        "commits": [],
        "problem": problem,
        "detail": detail,
        "skipped_missing_date": 0,
    }


def _problem(repository: str, kind: str, target: str, detail: str) -> dict[str, str]:
    return {"repository": repository, "kind": kind, "target": target, "detail": detail}


def _file_token(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coleta releases, tags e commits entre releases.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--repo", required=True, help="Repositorio no formato owner/name.")
    parser.add_argument("--default-branch", required=True)
    parser.add_argument("--lab-root", type=Path, default=LAB3_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    window = ObservationWindow.from_config(config)
    client = GitHubClient.from_environment()
    history = collect_release_history(
        client,
        repository=args.repo,
        default_branch=args.default_branch,
        window=window,
        lab_root=args.lab_root,
    )
    print(
        f"Coleta de {history.repository}: {len(history.releases)} releases, "
        f"{history.primary_count} na definicao principal, "
        f"{len(history.tags)} tags, {len(history.compares)} compares, "
        f"{len(history.problems)} registros de problema"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
