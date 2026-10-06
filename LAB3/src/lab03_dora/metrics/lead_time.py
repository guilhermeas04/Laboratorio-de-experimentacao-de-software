"""RQ02: lead time por release e por commit.

As funcoes nao consultam a API. A coleta entrega as datas; aqui so entra a conta.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence


@dataclass(frozen=True)
class ReleaseChanges:
    """Commits incluidos em uma release, ja resolvidos pelo compare."""

    tag_name: str
    published_at: datetime
    has_previous_release: bool
    commit_authored_at: tuple[datetime, ...]


@dataclass(frozen=True)
class ExcludedRelease:
    tag_name: str
    reason: str


@dataclass(frozen=True)
class LeadTimeSummary:
    by_release_days: float | None
    by_commit_days: float | None
    by_release_hours: float | None
    by_commit_hours: float | None
    release_values_days: tuple[float, ...]
    commit_values_days: tuple[float, ...]
    excluded: tuple[ExcludedRelease, ...]
    ignored_inconsistent_commits: int


def summarize_lead_time(releases: Sequence[ReleaseChanges]) -> LeadTimeSummary:
    """Mediana do lead time nas duas variantes obrigatorias.

    A primeira release do repositorio nao entra. Release sem commit novo tambem
    nao. Commit com data posterior a publicacao e inconsistente e fica de fora;
    se nao sobrar commit valido, a release inteira e excluida.
    """

    release_values: list[float] = []
    commit_values: list[float] = []
    excluded: list[ExcludedRelease] = []
    ignored_inconsistent = 0

    for release in releases:
        if not release.has_previous_release:
            excluded.append(ExcludedRelease(release.tag_name, "no_previous_release"))
            continue
        if not release.commit_authored_at:
            excluded.append(ExcludedRelease(release.tag_name, "no_new_commits"))
            continue

        valid_days: list[float] = []
        for authored_at in release.commit_authored_at:
            days = _days_between(release.published_at, authored_at)
            if days < 0:
                ignored_inconsistent += 1
                continue
            valid_days.append(days)

        if not valid_days:
            excluded.append(ExcludedRelease(release.tag_name, "inconsistent_dates"))
            continue

        release_values.append(max(valid_days))
        commit_values.extend(valid_days)

    by_release = _median(release_values)
    by_commit = _median(commit_values)
    return LeadTimeSummary(
        by_release_days=by_release,
        by_commit_days=by_commit,
        by_release_hours=None if by_release is None else by_release * 24,
        by_commit_hours=None if by_commit is None else by_commit * 24,
        release_values_days=tuple(release_values),
        commit_values_days=tuple(commit_values),
        excluded=tuple(excluded),
        ignored_inconsistent_commits=ignored_inconsistent,
    )


def release_changes(
    tag_name: str,
    published_at: str,
    commit_authored_at: Sequence[str],
    *,
    has_previous_release: bool,
) -> ReleaseChanges:
    """Monta a entrada da conta a partir de timestamps ISO da API."""

    return ReleaseChanges(
        tag_name=tag_name,
        published_at=_parse(published_at),
        has_previous_release=has_previous_release,
        commit_authored_at=tuple(_parse(value) for value in commit_authored_at),
    )


def _days_between(published_at: datetime, authored_at: datetime) -> float:
    return (_as_utc(published_at) - _as_utc(authored_at)).total_seconds() / 86400


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _as_utc(parsed)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))
