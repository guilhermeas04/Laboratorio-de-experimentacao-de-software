from lab03_dora.collection.selection import SelectionCriteria
from lab03_dora.pipeline.consolidate import build_dataset, deduplicate_rows
from lab03_dora.pipeline.expand_sample import split_star_range


def test_star_range_splits_when_search_hits_the_cap() -> None:
    assert split_star_range("1000..2000") == ["1000..1500", "1501..2000"]
    assert split_star_range("50001..*") == ["50001..55000", "55001..*"]


def test_duplicate_repository_keeps_the_first_row() -> None:
    kept, dropped = deduplicate_rows(
        [
            {"repository": "octo/one", "release_count": "1"},
            {"repository": "octo/one", "release_count": "9"},
            {"repository": "octo/two", "release_count": "6"},
        ]
    )

    assert dropped == 1
    assert [row["repository"] for row in kept] == ["octo/one", "octo/two"]
    assert kept[0]["release_count"] == "1"


def test_missing_lead_time_stays_blank() -> None:
    dataset, summary = build_dataset(
        [
            {
                "repository": "octo/one",
                "release_count": "6",
                "valid_workflow_runs_count": "50",
                "deployment_frequency_per_week": "0.1",
                "lead_time_by_release_days": "",
                "lead_time_by_commit_days": "",
                "cfr_ci": "",
            }
        ],
        SelectionCriteria(),
    )

    assert dataset[0]["lead_time_by_release_days"] == ""
    assert dataset[0]["lead_time_by_commit_days"] == ""
    assert dataset[0]["cfr_b"] == ""
    assert dataset[0]["eligible"] == "true"
    assert summary["eligible_count"] == 1
    assert summary["target_met"] is False


def test_repository_below_thresholds_is_not_eligible() -> None:
    dataset, summary = build_dataset(
        [
            {"repository": "octo/few", "release_count": "4", "valid_workflow_runs_count": "80"},
            {"repository": "octo/runs", "release_count": "8", "valid_workflow_runs_count": "10"},
        ],
        SelectionCriteria(),
    )

    assert dataset[0]["exclusion_reason"] == "insufficient_releases"
    assert dataset[1]["exclusion_reason"] == "insufficient_valid_workflow_runs"
    assert summary["eligible_count"] == 0
