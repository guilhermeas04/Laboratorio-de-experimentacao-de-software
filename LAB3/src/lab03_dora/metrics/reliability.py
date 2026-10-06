"""CFR(a) e tempo de recuperação de falhas de CI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from lab03_dora.collection.workflow_runs import VALID_CONCLUSIONS


def _timestamp(run: dict, *fields: str) -> datetime:
    for field in fields:
        value = run.get(field)
        if value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("workflow run sem fuso horário")
            return parsed.astimezone(UTC)
    raise ValueError("workflow run sem timestamp")


def _valid_runs(runs: list[dict]) -> list[dict]:
    return [
        run
        for run in runs
        if run.get("status") == "completed"
        and run.get("conclusion") in VALID_CONCLUSIONS
    ]


def calculate_cfr(runs: list[dict]) -> float | None:
    """Calcula falhas / (falhas + sucessos); None quando não há base válida."""
    valid = _valid_runs(runs)
    successes = sum(run["conclusion"] == "success" for run in valid)
    failures = sum(run["conclusion"] != "success" for run in valid)
    denominator = successes + failures
    return failures / denominator if denominator else None


@dataclass(frozen=True)
class RecoveryEpisode:
    started_at: str
    recovered_at: str | None
    recovery_hours: float | None
    censored: bool
    failure_count: int


@dataclass(frozen=True)
class RecoverySummary:
    episodes: list[RecoveryEpisode]

    @property
    def recovered_count(self) -> int:
        return sum(not episode.censored for episode in self.episodes)

    @property
    def censored_count(self) -> int:
        return sum(episode.censored for episode in self.episodes)


def calculate_recovery(
    runs: list[dict],
    *,
    observation_end: datetime | str,
) -> RecoverySummary:
    """Agrupa falhas consecutivas até o primeiro sucesso posterior.

    O episódio começa no início da primeira execução falha e termina no fim da
    primeira execução bem-sucedida. Sem sucesso até observation_end, o episódio
    é censurado e seu tempo vai até o fim da observação.
    """
    end = observation_end
    if isinstance(end, str):
        end = datetime.fromisoformat(end.replace("Z", "+00:00"))
    if end.tzinfo is None:
        raise ValueError("fim da observação deve conter fuso horário")
    end = end.astimezone(UTC)

    ordered = sorted(_valid_runs(runs), key=lambda run: _timestamp(run, "run_started_at", "created_at"))
    episodes: list[RecoveryEpisode] = []
    active_start: datetime | None = None
    active_failures = 0
    for run in ordered:
        conclusion = run["conclusion"]
        if conclusion != "success":
            if active_start is None:
                active_start = _timestamp(run, "run_started_at", "created_at")
                active_failures = 0
            active_failures += 1
            continue
        if active_start is None:
            continue
        recovered_at = _timestamp(run, "updated_at", "run_started_at", "created_at")
        episodes.append(
            RecoveryEpisode(
                started_at=active_start.isoformat(),
                recovered_at=recovered_at.isoformat(),
                recovery_hours=(recovered_at - active_start).total_seconds() / 3600,
                censored=False,
                failure_count=active_failures,
            )
        )
        active_start = None
        active_failures = 0

    if active_start is not None:
        episodes.append(
            RecoveryEpisode(
                started_at=active_start.isoformat(),
                recovered_at=None,
                recovery_hours=(end - active_start).total_seconds() / 3600,
                censored=True,
                failure_count=active_failures,
            )
        )
    return RecoverySummary(episodes=episodes)
