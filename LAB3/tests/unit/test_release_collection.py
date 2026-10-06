import json
from datetime import date
from pathlib import Path

from lab03_dora.api.github import GitHubApiError, GitHubResponse
from lab03_dora.collection.commits import collect_commits_between
from lab03_dora.collection.history import collect_many, collect_release_history
from lab03_dora.collection.observation import ObservationWindow
from lab03_dora.collection.releases import normalize_release, pair_with_previous
from lab03_dora.collection.tags import collect_tags


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "api"
WINDOW = ObservationWindow(start=date(2025, 1, 1), end=date(2025, 12, 31))


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeGitHub:
    def __init__(self, *, releases=None, tags=None, compares=None, commit_dates=None, fail=None):
        self.releases = releases or []
        self.tags = tags or []
        self.compares = compares or {}
        self.commit_dates = commit_dates or {}
        self.fail = set(fail or [])

    def paginate(self, path, params=None):
        if path.endswith("/releases"):
            if "releases" in self.fail:
                raise GitHubApiError("falha releases")
            yield from self.releases
            return
        if path.endswith("/tags"):
            if "tags" in self.fail:
                raise GitHubApiError("falha tags")
            yield from self.tags
            return
        raise AssertionError(path)

    def get(self, path, params=None):
        if "/compare/" in path:
            page = int((params or {}).get("page", 1))
            pages = self.compares[path]
            if isinstance(pages, Exception):
                raise pages
            return GitHubResponse(payload=pages[page - 1], headers={})
        if "/commits/" in path:
            sha = path.rsplit("/", 1)[-1]
            if sha in self.fail:
                raise GitHubApiError("commit da tag indisponivel")
            return GitHubResponse(
                payload={"commit": {"author": {"date": self.commit_dates[sha]}}},
                headers={},
            )
        raise AssertionError(path)


def test_primary_release_ignores_draft_prerelease_and_other_branch() -> None:
    records = [
        normalize_release(item, repository="octo/example", default_branch="main", window=WINDOW)
        for item in _load("releases.json")
    ]
    by_tag = {record.tag_name: record for record in records}

    assert by_tag["v1.1.0"].primary is True
    assert by_tag["v1.0.0"].primary is False
    assert by_tag["v1.0.0"].exclusion_reason == "outside_window"
    assert by_tag["v1.2.0-rc.1"].exclusion_reason == "prerelease"
    assert by_tag["v1.2.0"].exclusion_reason == "draft"
    assert by_tag["v9.0.0"].exclusion_reason == "outside_default_branch"
    assert by_tag[""].primary is True
    assert by_tag[""].warning == "missing_tag"

    pairs = pair_with_previous(records)
    previous_of_v11 = dict(pairs)[by_tag["v1.1.0"]]
    assert previous_of_v11 is not None
    assert previous_of_v11.tag_name == "v1.0.0"


def test_compare_paginates_and_keeps_commit_author_date() -> None:
    pages = _load("compare_v1.0.0_v1.1.0.json")
    client = FakeGitHub(compares={"/repos/octo/example/compare/v1.0.0...v1.1.0": pages})

    result, raw_pages = collect_commits_between(
        client,
        "octo/example",
        "v1.0.0",
        "v1.1.0",
        per_page=2,
    )

    assert [commit.authored_at for commit in result.commits] == [
        "2025-03-02T00:00:00Z",
        "2025-03-10T00:00:00Z",
        "2025-03-14T00:00:00Z",
    ]
    assert result.problem == ""
    assert len(raw_pages) == 2


def test_compare_records_missing_previous_tag_and_http_error() -> None:
    missing_previous, _ = collect_commits_between(FakeGitHub(), "octo/example", None, "v1.0.0")
    assert missing_previous.problem == "no_previous_release"

    missing_tag, _ = collect_commits_between(FakeGitHub(), "octo/example", "v1.0.0", "")
    assert missing_tag.problem == "missing_tag"

    client = FakeGitHub(
        compares={
            "/repos/octo/example/compare/v1.0.0...v1.1.0": GitHubApiError("GitHub API retornou HTTP 404"),
        }
    )
    failed, _ = collect_commits_between(client, "octo/example", "v1.0.0", "v1.1.0")
    assert failed.problem == "compare_error"
    assert "404" in failed.detail


def test_tags_use_commit_date_and_record_lookup_failure() -> None:
    tags = _load("tags.json")
    client = FakeGitHub(
        tags=tags,
        commit_dates={"1111111111111111111111111111111111111111": "2024-11-01T12:00:00Z"},
        fail={"3333333333333333333333333333333333333333"},
    )
    records, raw = collect_tags(client, "octo/example")

    assert raw[0]["name"] == "v1.0.0"
    assert records[0].commit_authored_at == "2024-11-01T12:00:00Z"
    assert records[1].commit_authored_at == "2025-03-14T00:00:00Z"
    assert records[1].problem == ""


def test_tag_lookup_failure_does_not_drop_the_tag() -> None:
    client = FakeGitHub(
        tags=[{"name": "v2", "commit": {"sha": "3333333333333333333333333333333333333333"}}],
        fail={"3333333333333333333333333333333333333333"},
    )

    records, _ = collect_tags(client, "octo/example")

    assert records[0].name == "v2"
    assert records[0].problem == "tag_commit_lookup_failed"


def test_history_writes_cache_and_continues_after_compare_error(tmp_path: Path) -> None:
    pages = _load("compare_v1.0.0_v1.1.0.json")
    client = FakeGitHub(
        releases=_load("releases.json"),
        tags=_load("tags.json"),
        compares={"/repos/octo/example/compare/v1.0.0...v1.1.0": pages},
        commit_dates={"1111111111111111111111111111111111111111": "2024-11-01T12:00:00Z"},
    )

    history = collect_release_history(
        client,
        repository="octo/example",
        default_branch="main",
        window=WINDOW,
        lab_root=tmp_path,
        compare_per_page=2,
    )

    kinds = {item["kind"] for item in history.problems}
    assert "draft" in kinds
    assert "prerelease" in kinds
    assert "outside_default_branch" in kinds
    assert "missing_tag" in kinds
    assert history.primary_count == 2
    assert (tmp_path / "cache" / "api" / "octo__example" / "releases.json").exists()
    assert (tmp_path / "data" / "raw" / "github" / "commits" / "octo__example.json").exists()
    saved_commits = json.loads((tmp_path / "data" / "raw" / "github" / "commits" / "octo__example.json").read_text())
    v11 = next(item for item in saved_commits if item["head_tag"] == "v1.1.0")
    assert len(v11["commits"]) == 3
    assert v11["problem"] == ""


def test_one_repository_failing_does_not_stop_the_next(tmp_path: Path) -> None:
    client = FakeGitHub(fail={"releases", "tags"})

    histories = collect_many(
        client,
        [("octo/broken", "main"), ("octo/also", "main")],
        window=WINDOW,
        lab_root=tmp_path,
    )

    assert len(histories) == 2
    assert histories[0].problems[0]["kind"] == "releases_request_failed"
    assert histories[1].repository == "octo/also"
