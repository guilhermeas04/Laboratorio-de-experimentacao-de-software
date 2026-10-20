from lab03_dora.analysis.rq01_rq02 import (
    classify_deployment_frequency,
    classify_lead_time,
    summarize_metric,
)


def test_summarize_metric_ignores_missing_values() -> None:
    summary = summarize_metric(
        [{"metric": "1"}, {"metric": ""}, {"metric": "3"}, {"metric": "5"}],
        "metric",
        "metric",
    )

    assert summary.n_total == 4
    assert summary.n_present == 3
    assert summary.n_missing == 1
    assert summary.median == 3
    assert summary.q1 == 2
    assert summary.q3 == 4
    assert summary.iqr == 2


def test_dora_classification_boundaries() -> None:
    assert classify_deployment_frequency(None) == "ausente"
    assert classify_deployment_frequency(7) == "Elite"
    assert classify_deployment_frequency(1) == "High"
    assert classify_deployment_frequency(1 / (365 / 7)) == "Medium"
    assert classify_lead_time(None) == "ausente"
    assert classify_lead_time(0.99) == "Elite"
    assert classify_lead_time(1) == "High"
    assert classify_lead_time(7) == "Medium"
    assert classify_lead_time(30) == "Low"