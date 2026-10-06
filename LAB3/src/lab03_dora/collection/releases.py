"""Normalizacao e classificacao de releases do GitHub."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from lab03_dora.collection.observation import ObservationWindow, in_observation_window, parse_github_timestamp


@dataclass(frozen=True)
class ReleaseRecord:
    """Release ja classificada para a definicao principal de deploy."""

    repository: str
    release_id: str
    tag_name: str
    name: str
    draft: bool
    prerelease: bool
    published_at: str
    target_commitish: str
    default_branch: str
    in_observation_window: bool
    on_default_branch: bool
    primary: bool
    exclusion_reason: str = ""
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_release(
    payload: dict[str, Any],
    *,
    repository: str,
    default_branch: str,
    window: ObservationWindow,
) -> ReleaseRecord:
    """Converte o JSON de uma release e aplica draft, janela e default branch."""

    tag_name = str(payload.get("tag_name") or "")
    published_at = str(payload.get("published_at") or "")
    target = str(payload.get("target_commitish") or "")
    draft = bool(payload.get("draft") or False)
    prerelease = bool(payload.get("prerelease") or False)
    on_branch, branch_note = _branch_status(target, default_branch)
    moment = parse_github_timestamp(published_at)
    inside_window = in_observation_window(moment, window)

    exclusion = ""
    warning = ""
    if draft:
        exclusion = "draft"
    elif prerelease:
        exclusion = "prerelease"
    elif moment is None:
        exclusion = "missing_published_at"
    elif not inside_window:
        exclusion = "outside_window"
    elif not on_branch:
        exclusion = branch_note or "outside_default_branch"
    else:
        warning = branch_note
        if not tag_name:
            warning = "missing_tag"

    return ReleaseRecord(
        repository=repository,
        release_id=str(payload.get("id") or ""),
        tag_name=tag_name,
        name=str(payload.get("name") or tag_name),
        draft=draft,
        prerelease=prerelease,
        published_at=published_at,
        target_commitish=target,
        default_branch=default_branch,
        in_observation_window=inside_window,
        on_default_branch=on_branch,
        primary=exclusion == "",
        exclusion_reason=exclusion,
        warning=warning,
    )


def deploy_releases(records: list[ReleaseRecord]) -> list[ReleaseRecord]:
    """Releases publicadas no default branch, inclusive fora da janela.

    A release anterior de um deploy da janela pode ter sido publicada antes
    do inicio da observacao. Draft e pre-release nao entram nessa historia.
    """

    selected = [
        record
        for record in records
        if not record.draft and not record.prerelease and record.published_at and record.on_default_branch
    ]
    return sorted(selected, key=lambda record: (record.published_at, record.release_id))


def pair_with_previous(records: list[ReleaseRecord]) -> list[tuple[ReleaseRecord, ReleaseRecord | None]]:
    """Pareia cada release primaria com a release publicada imediatamente anterior."""

    history = deploy_releases(records)
    index_by_id = {record.release_id: position for position, record in enumerate(history)}
    pairs: list[tuple[ReleaseRecord, ReleaseRecord | None]] = []
    for record in records:
        if not record.primary:
            continue
        position = index_by_id.get(record.release_id)
        if position is None:
            pairs.append((record, None))
            continue
        previous = history[position - 1] if position > 0 else None
        pairs.append((record, previous))
    return pairs


def _branch_status(target: str, default_branch: str) -> tuple[bool, str]:
    cleaned = target.strip()
    if cleaned == default_branch:
        return True, ""
    if len(cleaned) == 40 and all(character in "0123456789abcdefABCDEF" for character in cleaned):
        # A resposta de releases nao informa a ancestralidade do SHA. Ele e
        # mantido para evitar falso descarte, mas fica explicitamente marcado
        # para validacao posterior contra a default branch.
        return True, "unverified_target_commitish_sha"
    if not cleaned:
        return False, "missing_target_commitish"
    return False, "outside_default_branch"
