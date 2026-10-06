import json
import csv
from datetime import date
from pathlib import Path

from lab03_dora.api.github import GitHubApiError, GitHubResponse
from lab03_dora.collection.commits import collect_commits_between
from lab03_dora.collection.history import (
    collect_many,
    collect_release_history,
    main as history_main,
    release_change_rows,
    repositories_from_selection,
    update_selection_with_release_counts,
)
from lab03_dora.collection.observation import ObservationWindow
from lab03_dora.collection.releases import normalize_release, pair_with_previous
from lab03_dora.collection.selection import SelectionCriteria
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


def test_compare_collects_more_than_api_maximum_page_size() -> None:
    def commits(start: int, count: int) -> list[dict]:
        return [
            {
                "sha": f"{index:040x}",
                "commit": {
                    "author": {"date": "2025-03-02T00:00:00Z"},
                    "message": f"commit {index}",
                },
            }
            for index in range(start, start + count)
        ]

    pages = [
        {"total_commits": 150, "commits": commits(0, 100)},
        {"total_commits": 150, "commits": commits(100, 50)},
    ]
    client = FakeGitHub(compares={"/repos/octo/example/compare/v1...v2": pages})

    result, raw_pages = collect_commits_between(client, "octo/example", "v1", "v2", per_page=250)

    assert len(result.commits) == 150
    assert len(raw_pages) == 2
    assert result.problem == ""


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


def test_batch_selection_updates_counts_and_builds_lead_time_input(tmp_path: Path) -> None:
    selection = [
        {
            "full_name": "octo/example",
            "default_branch": "main",
            "has_actions": "True",
            "selection_status": "s01_base_sample",
            "releases_count": "",
            "valid_workflow_runs_count": "",
        },
        {
            "full_name": "octo/discarded",
            "default_branch": "main",
            "has_actions": "False",
            "selection_status": "discarded",
            "releases_count": "",
            "valid_workflow_runs_count": "",
        },
    ]
    assert repositories_from_selection(selection, limit=100) == [("octo/example", "main")]

    client = FakeGitHub(
        releases=_load("releases.json"),
        tags=_load("tags.json"),
        compares={
            "/repos/octo/example/compare/v1.0.0...v1.1.0": _load("compare_v1.0.0_v1.1.0.json")
        },
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
    histories = [history]
    updated = update_selection_with_release_counts(selection, histories, SelectionCriteria())
    inputs = release_change_rows(histories)

    assert updated[0]["releases_count"] == 2
    assert updated[0]["exclusion_reason"] == "insufficient_releases"
    v11 = next(row for row in inputs if row["tag_name"] == "v1.1.0")
    assert json.loads(v11["commit_authored_at"]) == [
        "2025-03-02T00:00:00Z",
        "2025-03-10T00:00:00Z",
        "2025-03-14T00:00:00Z",
    ]


def test_batch_cli_reads_selection_and_updates_release_count(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "observation_window": {"start": "2025-01-01", "end": "2025-12-31"},
                "selection": {
                    "target_s01_sample_size": 100,
                    "minimum_releases": 5,
                    "minimum_valid_workflow_runs": 50,
                },
            }
        ),
        encoding="utf-8",
    )
    selection = tmp_path / "selection.csv"
    with selection.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "full_name",
                "default_branch",
                "has_actions",
                "releases_count",
                "valid_workflow_runs_count",
                "selection_status",
                "exclusion_reason",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "full_name": "octo/empty",
                "default_branch": "main",
                "has_actions": "True",
                "releases_count": "",
                "valid_workflow_runs_count": "",
                "selection_status": "s01_base_sample",
                "exclusion_reason": "awaiting_releases_and_workflow_runs_counts",
            }
        )
    monkeypatch.setattr(
        "lab03_dora.collection.history.GitHubClient.from_environment",
        lambda **kwargs: FakeGitHub(),
    )
    changes = tmp_path / "release_changes.csv"
    funnel = tmp_path / "funnel.csv"

    result = history_main(
        [
            "--config",
            str(config),
            "--selection-csv",
            str(selection),
            "--funnel-output",
            str(funnel),
            "--release-changes-output",
            str(changes),
            "--lab-root",
            str(tmp_path),
        ]
    )

    assert result == 0
    with selection.open(newline="", encoding="utf-8") as file:
        updated = next(csv.DictReader(file))
    assert updated["releases_count"] == "0"
    assert updated["exclusion_reason"] == "insufficient_releases"
    assert funnel.exists()
    assert changes.read_text(encoding="utf-8").startswith("repository,tag_name,published_at")
