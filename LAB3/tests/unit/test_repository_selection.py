from lab03_dora.collection.repositories import (
    attach_actions_metadata,
    deduplicate_candidates,
    normalize_repository,
)
from lab03_dora.collection.selection import (
    SelectionCriteria,
    build_funnel,
    build_selection_table,
    classify_repository,
)


def test_normalize_repository_extracts_required_metadata() -> None:
    payload = {
        "full_name": "example/project",
        "name": "project",
        "owner": {"login": "example"},
        "default_branch": "main",
        "stargazers_count": 1500,
        "language": "Python",
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "pushed_at": "2025-01-02T00:00:00Z",
        "archived": False,
        "disabled": False,
    }

    candidate = normalize_repository(payload)

    assert candidate.full_name == "example/project"
    assert candidate.owner == "example"
    assert candidate.default_branch == "main"
    assert candidate.stars == 1500
    assert candidate.language == "Python"


def test_attach_actions_metadata_marks_repositories_without_actions() -> None:
    candidate = normalize_repository(
        {
            "full_name": "example/no-actions",
            "owner": {"login": "example"},
            "name": "no-actions",
        }
    )

    enriched = attach_actions_metadata(candidate, {"total_count": 0})

    assert enriched.has_actions is False
    assert enriched.selection_status == "discarded"
    assert enriched.exclusion_reason == "no_github_actions"


def test_deduplicate_candidates_preserves_first_occurrence() -> None:
    first = normalize_repository({"full_name": "example/project", "stargazers_count": 10})
    duplicate = normalize_repository({"full_name": "example/project", "stargazers_count": 20})

    result = deduplicate_candidates([first, duplicate])

    assert result == [first]


def test_classify_repository_waits_for_downstream_counts_when_missing() -> None:
    status, reason = classify_repository(
        {"has_actions": True, "archived": False, "disabled": False},
        SelectionCriteria(),
    )

    assert status == "pending_downstream_collection"
    assert reason == "requires_releases_or_workflow_runs_collection"


def test_selection_table_promotes_actions_repositories_to_s01_base_sample() -> None:
    selected = build_selection_table(
        [
            {
                "full_name": "example/pending",
                "has_actions": True,
                "archived": False,
                "disabled": False,
                "releases_count": "",
                "valid_workflow_runs_count": "",
            }
        ],
        SelectionCriteria(target_s01_sample_size=100),
    )

    assert selected[0]["selection_status"] == "s01_base_sample"
    assert selected[0]["exclusion_reason"] == "awaiting_releases_and_workflow_runs_counts"


def test_selection_table_limits_s01_sample_to_target_size() -> None:
    rows = [
        {
            "full_name": f"example/project-{index}",
            "has_actions": True,
            "archived": False,
            "disabled": False,
            "releases_count": 5,
            "valid_workflow_runs_count": 50,
        }
        for index in range(3)
    ]

    selected = build_selection_table(rows, SelectionCriteria(target_s01_sample_size=2))

    assert [row["selection_status"] for row in selected] == [
        "eligible_s01",
        "eligible_s01",
        "discarded",
    ]
    assert selected[-1]["exclusion_reason"] == "sample_limit_reached"


def test_build_funnel_counts_actions_and_elegible_sample() -> None:
    rows = build_selection_table(
        [
            {
                "full_name": "example/ok",
                "has_actions": True,
                "archived": False,
                "disabled": False,
                "releases_count": 6,
                "valid_workflow_runs_count": 60,
            },
            {
                "full_name": "example/no-actions",
                "has_actions": False,
                "archived": False,
                "disabled": False,
                "releases_count": 10,
                "valid_workflow_runs_count": 80,
            },
            {
                "full_name": "example/pending",
                "has_actions": True,
                "archived": False,
                "disabled": False,
                "releases_count": "",
                "valid_workflow_runs_count": "",
            },
        ],
        SelectionCriteria(target_s01_sample_size=100),
    )

    funnel = {row["stage"]: row["count"] for row in build_funnel(rows, SelectionCriteria())}

    assert funnel["candidates"] == 3
    assert funnel["with_github_actions"] == 2
    assert funnel["eligible_s01_sample"] == 1
    assert funnel["s01_base_sample"] == 1
    assert funnel["pending_downstream_collection"] == 0
