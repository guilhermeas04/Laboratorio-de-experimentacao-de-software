from lab03_dora.analysis.rq03_rq04 import classify_c1, classify_cfr, classify_recovery, summarize_metric


def test_summarize_metric_and_missing_values() -> None:
    summary = summarize_metric([{"metric": "0.1"}, {"metric": ""}, {"metric": "0.3"}], "metric", "cfr_a")

    assert summary.n_present == 2
    assert summary.n_missing == 1
    assert summary.median == 0.2
    assert summary.iqr == 0.1


def test_cfr_and_recovery_boundaries() -> None:
    assert classify_cfr(None) == "ausente"
    assert classify_cfr(0.15) == "Elite"
    assert classify_cfr(0.30) == "High"
    assert classify_cfr(0.45) == "Medium"
    assert classify_cfr(0.46) == "Low"
    assert classify_recovery(0.99) == "Elite"
    assert classify_recovery(1) == "High"
    assert classify_recovery(24) == "Medium"
    assert classify_recovery(168) == "Low"


def test_c1_requires_four_metrics_and_uses_floor_median() -> None:
    row = {
        "repository": "octo/example",
        "deployment_frequency_per_week": "1",
        "lead_time_by_release_days": "2",
        "cfr_ci": "0.2",
        "cfr_b": "0.1",
        "recovery_median_hours": "2",
        "eligible": "true",
    }

    result = classify_c1(row)
    assert result["c1_metric_count"] == 4
    assert result["c1_class"] == "High"
    row["recovery_median_hours"] = ""
    assert classify_c1(row)["c1_class"] == "ausente"