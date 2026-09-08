from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lab02 import MAX_TRIAL_SECONDS, TrialTimer, TrialTimerError


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock(datetime(2026, 9, 8, 22, 0, tzinfo=timezone.utc))


@pytest.fixture
def timer(tmp_path: Path, clock: MutableClock) -> TrialTimer:
    return TrialTimer(tmp_path / "sessions", tmp_path / "raw", clock=clock)


def start_ai_trial(timer: TrialTimer, trial_id: str = "P01-K01-AI") -> None:
    timer.start(
        trial_id=trial_id,
        participant="participant-01",
        kata_id="kata-01",
        treatment="with_ai",
        execution_order=1,
        assistant_name="assistente-exemplo",
        assistant_version="versao-exemplo",
    )


def test_start_persists_session_metadata(timer: TrialTimer, tmp_path: Path) -> None:
    start_ai_trial(timer)

    payload = json.loads((tmp_path / "sessions" / "P01-K01-AI.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0"
    assert payload["started_at"] == "2026-09-08T22:00:00+00:00"
    assert payload["assistant_name"] == "assistente-exemplo"


def test_start_rejects_duplicate_or_unsafe_identifier(timer: TrialTimer) -> None:
    start_ai_trial(timer)

    with pytest.raises(TrialTimerError, match="já foi iniciado"):
        start_ai_trial(timer)
    with pytest.raises(TrialTimerError, match="trial_id"):
        start_ai_trial(timer, "../fora")


def test_start_rejects_invalid_treatment_configuration(timer: TrialTimer) -> None:
    with pytest.raises(TrialTimerError, match="exige assistant_name"):
        timer.start(
            trial_id="P01-K01-AI",
            participant="participant-01",
            kata_id="kata-01",
            treatment="with_ai",
            execution_order=1,
        )

    with pytest.raises(TrialTimerError, match="manual não aceita"):
        timer.start(
            trial_id="P01-K01-MANUAL",
            participant="participant-01",
            kata_id="kata-01",
            treatment="manual",
            execution_order=1,
            assistant_name="indevido",
        )


def test_status_reports_elapsed_remaining_and_limit(
    timer: TrialTimer, clock: MutableClock
) -> None:
    start_ai_trial(timer)
    clock.advance(125.5)

    running = timer.status("P01-K01-AI")

    assert running.elapsed_seconds == 125.5
    assert running.remaining_seconds == MAX_TRIAL_SECONDS - 125.5
    assert running.time_box_reached is False

    clock.advance(MAX_TRIAL_SECONDS)
    expired = timer.status("P01-K01-AI")
    assert expired.elapsed_seconds == MAX_TRIAL_SECONDS
    assert expired.remaining_seconds == 0
    assert expired.time_box_reached is True


def test_finish_green_trial_writes_immutable_record(
    timer: TrialTimer, clock: MutableClock, tmp_path: Path
) -> None:
    start_ai_trial(timer)
    clock.advance(750.125)

    record, output_path = timer.finish(
        "P01-K01-AI", tests_total=12, tests_passing=12, prompt_count=4
    )

    assert record.censored is False
    assert record.elapsed_seconds == 750.125
    assert record.time_to_green_seconds == 750.125
    assert record.success_rate == 100
    assert output_path == tmp_path / "raw" / "P01-K01-AI.json"
    assert json.loads(output_path.read_text(encoding="utf-8"))["prompt_count"] == 4

    with pytest.raises(TrialTimerError, match="imutável"):
        timer.finish("P01-K01-AI", tests_total=12, tests_passing=12, prompt_count=4)


def test_finish_expired_trial_records_censoring_at_35_minutes(
    timer: TrialTimer, clock: MutableClock
) -> None:
    start_ai_trial(timer)
    clock.advance(MAX_TRIAL_SECONDS + 15)

    record, _ = timer.finish(
        "P01-K01-AI", tests_total=12, tests_passing=9, prompt_count=7
    )

    assert record.censored is True
    assert record.elapsed_seconds == MAX_TRIAL_SECONDS
    assert record.time_to_green_seconds is None
    assert record.success_rate == 75
    assert record.finished_at == "2026-09-08T22:35:00+00:00"


def test_finish_rejects_early_incomplete_or_late_ambiguous_result(
    timer: TrialTimer, clock: MutableClock, tmp_path: Path
) -> None:
    start_ai_trial(timer)
    clock.advance(100)

    with pytest.raises(TrialTimerError, match="ainda incompleto"):
        timer.finish("P01-K01-AI", tests_total=10, tests_passing=8)
    assert not (tmp_path / "raw" / "P01-K01-AI.json").exists()

    clock.advance(MAX_TRIAL_SECONDS)
    with pytest.raises(TrialTimerError, match="após o limite"):
        timer.finish("P01-K01-AI", tests_total=10, tests_passing=10)


@pytest.mark.parametrize(
    ("total", "passing", "message"),
    [(0, 0, "tests_total"), (10, 11, "tests_passing"), (10, -1, "tests_passing")],
)
def test_finish_rejects_invalid_test_counts(
    timer: TrialTimer, total: int, passing: int, message: str
) -> None:
    start_ai_trial(timer)

    with pytest.raises(TrialTimerError, match=message):
        timer.finish("P01-K01-AI", tests_total=total, tests_passing=passing)


def test_rejects_naive_or_reversed_clock(tmp_path: Path, clock: MutableClock) -> None:
    naive_timer = TrialTimer(tmp_path / "naive", tmp_path / "raw", clock=lambda: datetime.now())
    with pytest.raises(TrialTimerError, match="fuso horário"):
        start_ai_trial(naive_timer)

    timer = TrialTimer(tmp_path / "sessions", tmp_path / "raw", clock=clock)
    start_ai_trial(timer)
    clock.advance(-1)
    with pytest.raises(TrialTimerError, match="anterior ao início"):
        timer.status("P01-K01-AI")
