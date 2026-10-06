from lab03_dora.metrics import calculate_cfr, calculate_recovery


def run(run_id: int, conclusion: str, started: str, updated: str | None = None) -> dict:
    return {
        "id": run_id,
        "status": "completed",
        "conclusion": conclusion,
        "run_started_at": started,
        "updated_at": updated or started,
    }


def test_cfr_ignores_invalid_conclusions() -> None:
    runs = [
        run(1, "success", "2026-01-01T10:00:00Z"),
        run(2, "failure", "2026-01-01T11:00:00Z"),
        run(3, "cancelled", "2026-01-01T12:00:00Z"),
        {**run(4, "success", "2026-01-01T13:00:00Z"), "status": "in_progress"},
    ]

    assert calculate_cfr(runs) == 0.5


def test_recovery_closes_episode_at_next_success() -> None:
    summary = calculate_recovery(
        [
            run(1, "failure", "2026-01-01T10:00:00Z", "2026-01-01T10:30:00Z"),
            run(2, "failure", "2026-01-01T11:00:00Z", "2026-01-01T11:20:00Z"),
            run(3, "success", "2026-01-01T12:30:00Z"),
        ],
        observation_end="2026-01-02T00:00:00Z",
    )

    assert summary.recovered_count == 1
    assert summary.episodes[0].censored is False
    assert summary.episodes[0].failure_count == 2
    assert summary.episodes[0].recovery_hours == 2.5


def test_recovery_marks_failure_without_success_as_censored() -> None:
    summary = calculate_recovery(
        [run(1, "failure", "2026-01-01T10:00:00Z", "2026-01-01T10:30:00Z")],
        observation_end="2026-01-01T12:30:00Z",
    )

    assert summary.censored_count == 1
    assert summary.episodes[0].recovered_at is None
    assert summary.episodes[0].recovery_hours == 2.5
