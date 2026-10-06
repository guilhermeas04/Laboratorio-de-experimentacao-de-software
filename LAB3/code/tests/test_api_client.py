import json
from pathlib import Path

from lab03_dora.api import GitHubApiClient


class FakeResponse:
    status = 200

    def __init__(self, payload: dict, headers: dict[str, str] | None = None) -> None:
        self.payload = payload
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_client_waits_for_rate_limit_and_reuses_cache(tmp_path: Path) -> None:
    sleeps: list[float] = []
    calls: list[object] = []

    def opener(request, timeout):
        calls.append(request)
        return FakeResponse(
            {"workflow_runs": []},
            {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "110"},
        )

    client = GitHubApiClient(
        "super-secret-token",
        cache_dir=tmp_path,
        clock=lambda: 100,
        sleep=sleeps.append,
        opener=opener,
    )

    client.get_json("repos/org/project/actions/runs", {"page": 1})
    client.get_json("repos/org/project/actions/runs", {"page": 1})

    assert sleeps == [10]
    assert len(calls) == 1
    cached = next(tmp_path.glob("*.json")).read_text(encoding="utf-8")
    assert "super-secret-token" not in cached


def test_client_retries_temporary_5xx_with_backoff(tmp_path: Path) -> None:
    sleeps: list[float] = []
    statuses = iter([500, 200])

    class Response(FakeResponse):
        def __init__(self, status: int):
            self.status = status
            self.headers = {}

    def opener(request, timeout):
        response = Response(next(statuses))
        response.payload = {"ok": True}
        return response

    client = GitHubApiClient(
        "token",
        cache_dir=tmp_path,
        sleep=sleeps.append,
        opener=opener,
    )

    assert client.get_json("status", {}) == {"ok": True}
    assert sleeps == [1]
