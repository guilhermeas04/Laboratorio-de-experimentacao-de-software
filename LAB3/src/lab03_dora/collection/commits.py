"""Commits entre duas releases, via compare paginado."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import quote

from lab03_dora.api.github import GitHubApiError
from lab03_dora.collection.tags import GitHubReader


MAX_COMPARE_PAGES = 20


@dataclass(frozen=True)
class CommitRecord:
    sha: str
    authored_at: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompareResult:
    repository: str
    base_tag: str
    head_tag: str
    commits: tuple[CommitRecord, ...]
    problem: str = ""
    detail: str = ""
    skipped_missing_date: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["commits"] = [commit.to_dict() for commit in self.commits]
        return payload


def collect_commits_between(
    client: GitHubReader,
    repository: str,
    base_tag: str | None,
    head_tag: str,
    *,
    per_page: int = 250,
) -> tuple[CompareResult, list[dict[str, Any]]]:
    """Busca os commits de base...head.

    Release sem anterior, tag ausente e erro de compare viram resultado
    registrado. Nenhum desses casos propaga a excecao para o restante da coleta.
    """

    if not base_tag:
        return _problem(repository, "", head_tag, "no_previous_release", "Nao ha release anterior para comparar."), []
    if not head_tag or not base_tag.strip():
        return _problem(repository, base_tag or "", head_tag, "missing_tag", "A release nao tem tag_name."), []

    raw_pages: list[dict[str, Any]] = []
    collected: list[CommitRecord] = []
    seen: set[str] = set()
    skipped = 0
    total_commits: int | None = None
    try:
        for page in range(1, MAX_COMPARE_PAGES + 1):
            response = client.get(
                f"/repos/{repository}/compare/{_compare_ref(base_tag, head_tag)}",
                {"per_page": per_page, "page": page},
            )
            payload = response.payload if isinstance(response.payload, dict) else {}
            raw_pages.append(payload)
            if not isinstance(response.payload, dict):
                return (
                    _problem(repository, base_tag, head_tag, "compare_error", "O compare nao retornou um objeto."),
                    raw_pages,
                )
            reported_total = payload.get("total_commits")
            if isinstance(reported_total, int):
                total_commits = reported_total
            page_commits = payload.get("commits") or []
            if not isinstance(page_commits, list):
                return (
                    _problem(repository, base_tag, head_tag, "compare_error", "O campo commits nao e uma lista."),
                    raw_pages,
                )
            new_on_page = 0
            for item in page_commits:
                if not isinstance(item, dict):
                    skipped += 1
                    continue
                parsed = _commit_from_payload(item)
                if parsed is None:
                    skipped += 1
                    continue
                if parsed.sha in seen:
                    continue
                seen.add(parsed.sha)
                collected.append(parsed)
                new_on_page += 1
            if new_on_page == 0 or len(page_commits) < per_page:
                break
            if total_commits is not None and len(collected) >= total_commits:
                break
        else:
            return (
                CompareResult(
                    repository=repository,
                    base_tag=base_tag,
                    head_tag=head_tag,
                    commits=tuple(collected),
                    problem="compare_truncated",
                    detail=f"A paginacao parou em {MAX_COMPARE_PAGES} paginas.",
                    skipped_missing_date=skipped,
                ),
                raw_pages,
            )
    except GitHubApiError as error:
        return _problem(repository, base_tag, head_tag, "compare_error", str(error)), raw_pages

    problem = ""
    detail = ""
    if not collected:
        problem = "no_new_commits"
        detail = "O compare nao trouxe commits novos com data de autor."
    elif skipped:
        problem = "missing_commit_date"
        detail = f"{skipped} commit(s) sem sha ou author.date foram ignorados."
    return (
        CompareResult(
            repository=repository,
            base_tag=base_tag,
            head_tag=head_tag,
            commits=tuple(collected),
            problem=problem,
            detail=detail,
            skipped_missing_date=skipped,
        ),
        raw_pages,
    )


def _compare_ref(base_tag: str, head_tag: str) -> str:
    return f"{quote(base_tag, safe='')}...{quote(head_tag, safe='')}"


def _commit_from_payload(item: dict[str, Any]) -> CommitRecord | None:
    sha = str(item.get("sha") or "")
    commit = item.get("commit") or {}
    author = commit.get("author") or {}
    authored_at = str(author.get("date") or "") if isinstance(author, dict) else ""
    if not sha or not authored_at:
        return None
    message = str(commit.get("message") or "").splitlines()[0]
    return CommitRecord(sha=sha, authored_at=authored_at, message=message)


def _problem(repository: str, base_tag: str, head_tag: str, problem: str, detail: str) -> CompareResult:
    return CompareResult(
        repository=repository,
        base_tag=base_tag,
        head_tag=head_tag,
        commits=(),
        problem=problem,
        detail=detail,
    )
