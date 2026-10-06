from pathlib import Path

from lab03_dora.api.github import GitHubClient, GitHubResponse


def test_get_reuses_cached_response_without_second_request(tmp_path: Path, monkeypatch) -> None:
    calls = []
    client = GitHubClient(token="secret", cache_dir=tmp_path)

    def fake_request(url: str) -> GitHubResponse:
        calls.append(url)
        return GitHubResponse({"value": 1}, {})

    monkeypatch.setattr(client, "_request_json", fake_request)
    assert client.get("/rate_limit").payload == {"value": 1}
    assert client.get("/rate_limit").payload == {"value": 1}
    assert len(calls) == 1
    assert "secret" not in next(tmp_path.glob("*.json")).read_text(encoding="utf-8")


def test_paginate_uses_retryable_get_path_and_follow_next_link(tmp_path: Path, monkeypatch) -> None:
    calls = []
    client = GitHubClient(token="secret", cache_dir=tmp_path)

    def fake_request(url: str) -> GitHubResponse:
        calls.append(url)
        if "page=2" in url:
            return GitHubResponse([{"id": 2}], {})
        return GitHubResponse(
            [{"id": 1}],
            {"link": '<https://api.github.com/items?page=2>; rel="next"'},
        )

    monkeypatch.setattr(client, "_request_json", fake_request)
    assert list(client.paginate("/items", {"page": 1})) == [{"id": 1}, {"id": 2}]
    assert len(calls) == 2
