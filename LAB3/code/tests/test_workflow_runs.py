from datetime import UTC, datetime
import json
from pathlib import Path

from lab03_dora.collection import collect_workflow_runs, classify_conclusion, month_windows


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str | int]]] = []

    def list_runs(self, repository: str, params: dict[str, str | int]) -> dict:
        self.calls.append((repository, params))
        return {
            "total_count": 1000,
            "workflow_runs": [
                {"id": 1, "status": "completed", "conclusion": "success", "event": "push"},
                {"id": 2, "status": "completed", "conclusion": "cancelled", "event": "push"},
                {"id": 3, "status": "in_progress", "conclusion": None, "event": "push"},
            ],
        }


def test_classifies_only_conclusions_valid_for_dora() -> None:
    assert classify_conclusion("SUCCESS") == "success"
    assert classify_conclusion("timed_out") == "timed_out"
    assert classify_conclusion("cancelled") is None
    assert classify_conclusion(None) is None


def test_month_windows_cover_boundary_without_overlap() -> None:
    windows = month_windows("2026-01-15T00:00:00+00:00", "2026-03-10T00:00:00+00:00")

    assert windows == [
        (
            datetime(2026, 1, 15, tzinfo=UTC),
            datetime(2026, 2, 1, tzinfo=UTC),
        ),
        (
            datetime(2026, 2, 1, tzinfo=UTC),
            datetime(2026, 3, 1, tzinfo=UTC),
        ),
        (
            datetime(2026, 3, 1, tzinfo=UTC),
            datetime(2026, 3, 10, tzinfo=UTC),
        ),
    ]


def test_collects_default_branch_push_runs_and_marks_api_limit(tmp_path: Path) -> None:
    client = FakeClient()

    result = collect_workflow_runs(
        "org/project",
        "main",
        "2026-01-01T00:00:00+00:00",
        "2026-02-01T00:00:00+00:00",
        client,
        cache_dir=tmp_path,
    )

    assert [run["id"] for run in result.runs] == [1]
    assert result.windows_at_limit == ["2026-01"]
    assert client.calls[0][0] == "org/project"
    assert client.calls[0][1]["event"] == "push"
    assert client.calls[0][1]["branch"] == "main"
    assert json.loads(next(tmp_path.glob("*.json")).read_text())


def test_uses_cache_without_second_api_call(tmp_path: Path) -> None:
    client = FakeClient()
    kwargs = {
        "repository": "org/project",
        "default_branch": "main",
        "start": "2026-01-01T00:00:00+00:00",
        "end": "2026-02-01T00:00:00+00:00",
        "cache_dir": tmp_path,
    }

    collect_workflow_runs(client=client, **kwargs)
    collect_workflow_runs(client=client, **kwargs)

    assert len(client.calls) == 1
