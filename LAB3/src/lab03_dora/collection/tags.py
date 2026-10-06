"""Coleta de tags para a analise de sensibilidade da RQ 07."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol

from lab03_dora.api.github import GitHubApiError, GitHubResponse


class GitHubReader(Protocol):
    def get(self, path: str, params: dict[str, Any] | None = None) -> GitHubResponse:
        """Uma chamada GET."""

    def paginate(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Itens de um endpoint paginado."""


@dataclass(frozen=True)
class TagRecord:
    repository: str
    name: str
    sha: str
    commit_authored_at: str
    problem: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_tags(client: GitHubReader, repository: str) -> tuple[list[TagRecord], list[dict[str, Any]]]:
    """Lista as tags e preenche a data com o commit apontado.

    A API de tags nao traz data. Se a consulta do commit falhar, a tag continua
    na saida com o problema registrado.
    """

    raw_pages: list[dict[str, Any]] = []
    records: list[TagRecord] = []
    for payload in client.paginate(f"/repos/{repository}/tags", {"per_page": 100}):
        if isinstance(payload, dict):
            raw_pages.append(payload)
        records.append(_tag_from_payload(client, repository, payload if isinstance(payload, dict) else {}))
    return records, raw_pages


def _tag_from_payload(client: GitHubReader, repository: str, payload: dict[str, Any]) -> TagRecord:
    name = str(payload.get("name") or "")
    commit = payload.get("commit") or {}
    sha = str(commit.get("sha") or "")
    embedded = _author_date(commit)
    if embedded:
        return TagRecord(repository=repository, name=name, sha=sha, commit_authored_at=embedded)
    if not sha:
        return TagRecord(
            repository=repository,
            name=name,
            sha="",
            commit_authored_at="",
            problem="tag_without_commit",
            detail="A tag nao trouxe o SHA do commit.",
        )
    try:
        response = client.get(f"/repos/{repository}/commits/{sha}")
    except GitHubApiError as error:
        return TagRecord(
            repository=repository,
            name=name,
            sha=sha,
            commit_authored_at="",
            problem="tag_commit_lookup_failed",
            detail=str(error),
        )
    body = response.payload if isinstance(response.payload, dict) else {}
    authored_at = _author_date(body.get("commit") or {})
    if not authored_at:
        return TagRecord(
            repository=repository,
            name=name,
            sha=sha,
            commit_authored_at="",
            problem="tag_commit_lookup_failed",
            detail="O commit da tag nao trouxe author.date.",
        )
    return TagRecord(repository=repository, name=name, sha=sha, commit_authored_at=authored_at)


def _author_date(commit_payload: dict[str, Any]) -> str:
    author = commit_payload.get("author") or {}
    if isinstance(author, dict) and author.get("date"):
        return str(author["date"])
    return ""
