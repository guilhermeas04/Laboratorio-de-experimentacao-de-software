"""CFR(b): falhas de releases e heuristica de release corretiva."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable, Mapping

CORRECTIVE_MESSAGE = re.compile(r"\b(?:fix|hotfix|revert)\b", re.IGNORECASE)
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
DATE_TAG = re.compile(r"^(?:19|20)\d{2}\.(?:0[1-9]|1[0-2])\.(?:0[1-9]|[12]\d|3[01])$")


@dataclass(frozen=True)
class ReleaseOutcome:
    repository: str
    release_id: str
    tag_name: str
    published_at: str
    prediction: str
    evaluated: bool
    censored: bool
    corrective_release: str
    next_release_tag: str
    days_to_next_release: float | None
    patch_signal: bool
    message_signal: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CfrBSummary:
    outcomes: list[ReleaseOutcome]

    @property
    def evaluated_count(self) -> int:
        return sum(item.evaluated for item in self.outcomes)

    @property
    def failed_count(self) -> int:
        return sum(item.prediction == "corretiva" for item in self.outcomes if item.evaluated)

    @property
    def censored_count(self) -> int:
        return sum(item.censored for item in self.outcomes)

    @property
    def cfr(self) -> float | None:
        return self.failed_count / self.evaluated_count if self.evaluated_count else None


def is_patch_transition(previous_tag: str, next_tag: str) -> bool:
    """Detecta somente transições SemVer; tags de calendário não são SemVer."""

    previous_text = previous_tag.strip()
    next_text = next_tag.strip()
    if DATE_TAG.fullmatch(previous_text) or DATE_TAG.fullmatch(next_text):
        return False
    previous = SEMVER.fullmatch(previous_text)
    following = SEMVER.fullmatch(next_text)
    if not previous or not following:
        return False
    previous_major, previous_minor, previous_patch = map(int, previous.groups()[:3])
    next_major, next_minor, next_patch = map(int, following.groups()[:3])
    return (
        previous_major == next_major
        and previous_minor == next_minor
        and next_patch > previous_patch
    )


def has_corrective_message(commits: Iterable[Mapping[str, Any]]) -> bool:
    """Retorna verdadeiro quando um commit comparado contém palavra corretiva."""

    return any(CORRECTIVE_MESSAGE.search(str(commit.get("message") or "")) for commit in commits)


def classify_corrective_release(
    previous: Mapping[str, Any],
    following: Mapping[str, Any],
    compare: Mapping[str, Any] | None = None,
) -> tuple[bool, bool, bool]:
    """Classifica uma release e retorna (corretiva, sinal_patch, sinal_mensagem)."""

    patch_signal = is_patch_transition(
        str(previous.get("tag_name") or ""), str(following.get("tag_name") or "")
    )
    message_signal = has_corrective_message((compare or {}).get("commits") or [])
    return patch_signal or message_signal, patch_signal, message_signal


def calculate_cfr_b(
    releases: Iterable[Mapping[str, Any]],
    compares: Iterable[Mapping[str, Any]],
    *,
    observation_end: datetime | str,
    window_days: int = 7,
) -> CfrBSummary:
    """Calcula CFR(b), preservando releases censuradas à direita."""

    end = _timestamp(observation_end)
    cutoff = end - timedelta(days=window_days)
    ordered = sorted(
        (release for release in releases if release.get("primary")),
        key=lambda release: (_timestamp(release.get("published_at")), str(release.get("release_id") or "")),
    )
    compare_by_head = {str(item.get("head_tag") or ""): item for item in compares}
    outcomes: list[ReleaseOutcome] = []
    for index, release in enumerate(ordered):
        published = _timestamp(release.get("published_at"))
        censored = published > cutoff
        following = ordered[index + 1] if index + 1 < len(ordered) else None
        days_to_next = None
        corrective = False
        patch_signal = False
        message_signal = False
        if following is not None:
            days_to_next = (_timestamp(following.get("published_at")) - published).total_seconds() / 86400
            if 0 <= days_to_next <= window_days:
                corrective, patch_signal, message_signal = classify_corrective_release(
                    release, following, compare_by_head.get(str(following.get("tag_name") or ""))
                )
        outcomes.append(
            ReleaseOutcome(
                repository=str(release.get("repository") or ""),
                release_id=str(release.get("release_id") or ""),
                tag_name=str(release.get("tag_name") or ""),
                published_at=str(release.get("published_at") or ""),
                prediction="corretiva" if corrective else "nao_corretiva",
                evaluated=not censored,
                censored=censored,
                corrective_release=str(following.get("release_id") or "") if corrective and following else "",
                next_release_tag=str(following.get("tag_name") or "") if following else "",
                days_to_next_release=days_to_next,
                patch_signal=patch_signal,
                message_signal=message_signal,
            )
        )
    return CfrBSummary(outcomes)


def _timestamp(value: datetime | str | Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
    return parsed.astimezone(UTC)
