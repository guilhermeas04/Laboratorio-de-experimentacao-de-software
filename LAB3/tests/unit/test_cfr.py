from lab03_dora.metrics import calculate_cfr_b, is_patch_transition
from lab03_dora.validation.labels import validate_gold_standard


def release(release_id: str, tag: str, published_at: str) -> dict:
    return {
        "repository": "octo/example",
        "release_id": release_id,
        "tag_name": tag,
        "published_at": published_at,
        "primary": True,
    }


def test_patch_transition_requires_same_major_and_minor() -> None:
    assert is_patch_transition("v2.3.0", "v2.3.1")
    assert not is_patch_transition("v2.3.0", "v2.4.0")
    assert not is_patch_transition("2025.06.06", "2025.06.07")


def test_cfr_b_uses_patch_or_message_and_preserves_censoring() -> None:
    releases = [
        release("1", "v2.3.0", "2025-12-01T00:00:00Z"),
        release("2", "v2.3.1", "2025-12-03T00:00:00Z"),
        release("3", "v3.0.0", "2025-12-10T00:00:00Z"),
        release("4", "v3.1.0", "2025-12-29T00:00:00Z"),
    ]
    summary = calculate_cfr_b(
        releases,
        [{"head_tag": "v2.3.1", "commits": []}, {"head_tag": "v3.0.0", "commits": [{"message": "hotfix: crash"}]}],
        observation_end="2025-12-31T23:59:59Z",
    )

    assert summary.failed_count == 2
    assert summary.evaluated_count == 3
    assert summary.censored_count == 1
    assert summary.cfr == 2 / 3
    assert summary.outcomes[0].patch_signal is True
    assert summary.outcomes[1].message_signal is True


def test_gold_standard_excludes_sem_release_and_reports_confusion_matrix() -> None:
    result = validate_gold_standard(
        [
            {"repository": "r", "release_id": "1", "consensus_label": "corretiva"},
            {"repository": "r", "release_id": "2", "consensus_label": "nao_corretiva"},
            {"repository": "r", "release_id": "3", "consensus_label": "sem_release"},
        ],
        [
            {"repository": "r", "release_id": "1", "prediction": "corretiva"},
            {"repository": "r", "release_id": "2", "prediction": "corretiva"},
        ],
    )

    assert result["n"] == 2
    assert result["precision"] == 0.5
    assert result["recall"] == 1.0
    assert result["confusion_matrix"] == {"true_negative": 0, "false_positive": 1, "false_negative": 0, "true_positive": 1}
    assert result["excluded_non_evaluable_count"] == 1
