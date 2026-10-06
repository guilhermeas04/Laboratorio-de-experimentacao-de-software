"""Repository candidate selection for LAB3S01."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class RepositoryCandidate:
    """Repository metadata needed before the DORA-specific collection steps."""

    full_name: str
    owner: str
    name: str
    default_branch: str
    stars: int
    language: str
    created_at: str
    updated_at: str
    pushed_at: str
    archived: bool
    disabled: bool
    has_actions: bool | None = None
    workflows_count: int | None = None
    releases_count: int | None = None
    valid_workflow_runs_count: int | None = None
    selection_status: str = "candidate"
    exclusion_reason: str = ""

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


def normalize_repository(payload: dict[str, Any]) -> RepositoryCandidate:
    """Convert a GitHub repository payload into the project schema."""

    owner_payload = payload.get("owner") or {}
    full_name = str(payload.get("full_name") or "")
    if "/" in full_name:
        owner, name = full_name.split("/", 1)
    else:
        owner = str(owner_payload.get("login") or "")
        name = str(payload.get("name") or "")
        full_name = f"{owner}/{name}" if owner and name else full_name

    return RepositoryCandidate(
        full_name=full_name,
        owner=owner,
        name=name,
        default_branch=str(payload.get("default_branch") or ""),
        stars=int(payload.get("stargazers_count") or 0),
        language=str(payload.get("language") or ""),
        created_at=str(payload.get("created_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
        pushed_at=str(payload.get("pushed_at") or ""),
        archived=bool(payload.get("archived") or False),
        disabled=bool(payload.get("disabled") or False),
    )


def attach_actions_metadata(
    candidate: RepositoryCandidate,
    workflows_payload: dict[str, Any] | None,
) -> RepositoryCandidate:
    """Return a candidate enriched with GitHub Actions availability."""

    workflows_count = int((workflows_payload or {}).get("total_count") or 0)
    has_actions = workflows_count > 0
    return RepositoryCandidate(
        **{
            **candidate.to_row(),
            "has_actions": has_actions,
            "workflows_count": workflows_count,
            "selection_status": "has_actions" if has_actions else "discarded",
            "exclusion_reason": "" if has_actions else "no_github_actions",
        }
    )


def deduplicate_candidates(candidates: Iterable[RepositoryCandidate]) -> list[RepositoryCandidate]:
    """Keep the first occurrence of each repository, preserving order."""

    seen: set[str] = set()
    deduplicated: list[RepositoryCandidate] = []
    for candidate in candidates:
        if candidate.full_name in seen:
            continue
        seen.add(candidate.full_name)
        deduplicated.append(candidate)
    return deduplicated
