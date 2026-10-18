import csv
from datetime import date

from lab03_dora.collection.observation import ObservationWindow
from lab03_dora.pipeline.expand_sample import _load_state, _collect_runs_fast


def test_import_existing_dataset_without_claiming_historical_rejects(tmp_path):
    path = tmp_path / "data/processed/datasets/s02_metrics.csv"
    path.parent.mkdir(parents=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["repository", "release_count", "valid_workflow_runs_count"])
        writer.writeheader()
        writer.writerow(dict(repository="a/b", release_count=5, valid_workflow_runs_count=50))
    state = _load_state(tmp_path)
    assert state["seen"] == ["a/b"]
    assert state["funnel"]["eligible"] == 1
    assert state["funnel"]["candidates"] == 1
    assert path.with_suffix(".baseline.csv").read_bytes() == path.read_bytes()


def test_runs_split_at_api_limit_and_deduplicate(tmp_path):
    class Client:
        calls = []
        def get(self, endpoint, params):
            self.calls.append(params)
            raw = dict(id=1, event="push", head_branch="main", status="completed", conclusion="success", created_at="2025-01-01T00:00:00Z")
            payload = {"total_count": 1000, "workflow_runs": []} if len(self.calls) == 1 else {"total_count": 1, "workflow_runs": [raw]}
            return type("Response", (), {"payload": payload})()
    client = Client()
    result = _collect_runs_fast(client, "a/b", "main", ObservationWindow(date(2025, 1, 1), date(2025, 12, 31)), None, tmp_path)
    assert len(client.calls) == 3
    assert len(result.runs) == 1
    assert result.windows_at_limit == []
