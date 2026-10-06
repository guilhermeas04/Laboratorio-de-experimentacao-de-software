import json
from datetime import datetime
from pathlib import Path

from lab03_dora.metrics.lead_time import ReleaseChanges, release_changes, summarize_lead_time


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "metrics" / "lead_time_v11.json"


def test_manual_example_of_v11() -> None:
    example = json.loads(FIXTURE.read_text(encoding="utf-8"))
    summary = summarize_lead_time(
        [
            release_changes(
                example["tag_name"],
                example["published_at"],
                example["commit_authored_at"],
                has_previous_release=True,
            )
        ]
    )

    assert summary.release_values_days == (example["expected_release_days"],)
    assert summary.commit_values_days == tuple(example["expected_commit_days"])
    assert summary.by_release_days == 13
    assert summary.by_commit_days == 5
    assert summary.by_release_hours == 13 * 24
    assert summary.by_commit_hours == 5 * 24


def test_release_median_and_commit_median_diverge_when_one_commit_is_old() -> None:
    summary = summarize_lead_time(
        [
            release_changes(
                "v1.1",
                "2025-03-15T00:00:00Z",
                ["2025-03-02T00:00:00Z", "2025-03-10T00:00:00Z", "2025-03-14T00:00:00Z"],
                has_previous_release=True,
            ),
            release_changes(
                "v1.2",
                "2025-05-20T00:00:00Z",
                ["2025-04-10T00:00:00Z", "2025-05-19T00:00:00Z"],
                has_previous_release=True,
            ),
        ]
    )

    assert summary.release_values_days == (13, 40)
    assert summary.by_release_days == 26.5
    assert summary.commit_values_days == (13, 5, 1, 40, 1)
    assert summary.by_commit_days == 5


def test_first_release_without_previous_is_ignored() -> None:
    summary = summarize_lead_time(
        [
            release_changes(
                "v1.0.0",
                "2025-03-15T00:00:00Z",
                ["2025-03-02T00:00:00Z"],
                has_previous_release=False,
            )
        ]
    )

    assert summary.by_release_days is None
    assert summary.by_commit_days is None
    assert _reasons(summary) == [("v1.0.0", "no_previous_release")]


def test_release_without_new_commits_is_ignored() -> None:
    summary = summarize_lead_time(
        [
            release_changes("v1.1.0", "2025-03-15T00:00:00Z", [], has_previous_release=True)
        ]
    )

    assert summary.by_release_days is None
    assert _reasons(summary) == [("v1.1.0", "no_new_commits")]


def test_naive_datetimes_are_read_as_utc() -> None:
    summary = summarize_lead_time(
        [
            ReleaseChanges(
                tag_name="v1.1",
                published_at=datetime(2025, 3, 15),
                has_previous_release=True,
                commit_authored_at=(datetime(2025, 3, 2),),
            )
        ]
    )

    assert summary.by_release_days == 13


def test_commit_after_release_is_an_inconsistent_date() -> None:
    summary = summarize_lead_time(
        [
            release_changes(
                "v1.1.0",
                "2025-03-15T00:00:00Z",
                ["2025-03-16T00:00:00Z"],
                has_previous_release=True,
            ),
            release_changes(
                "v1.2.0",
                "2025-04-10T00:00:00Z",
                ["2025-04-01T00:00:00Z", "2025-04-11T00:00:00Z"],
                has_previous_release=True,
            ),
        ]
    )

    assert _reasons(summary) == [("v1.1.0", "inconsistent_dates")]
    assert summary.ignored_inconsistent_commits == 2
    assert summary.release_values_days == (9,)
    assert summary.commit_values_days == (9,)


def _reasons(summary) -> list[tuple[str, str]]:
    return [(item.tag_name, item.reason) for item in summary.excluded]
