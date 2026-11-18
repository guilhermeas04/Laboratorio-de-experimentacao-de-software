from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab05_real_software.analysis import load_pilot_metrics
from lab05_real_software.impact import (
    ImpactEstimationError,
    estimate_latency_impact,
    plot_latency_comparison,
    run_impact_report,
)

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "pilot_metrics.csv"
STUDY = ROOT / "config" / "study.json"


def test_estimate_is_reproducible_and_marked_as_estimate():
    frame = load_pilot_metrics(FIXTURE)
    first = estimate_latency_impact(frame, queries_per_day=1000, working_days_per_year=10)
    second = estimate_latency_impact(frame, queries_per_day=1000, working_days_per_year=10)
    assert first == second
    assert first["kind"] == "estimate"
    assert first["mean_difference_ms"] > 0
    assert first["estimated_hours_saved_per_year"] > 0
    assert "Estimativa" in first["caveat"]


def test_estimate_scales_with_query_volume():
    frame = load_pilot_metrics(FIXTURE)
    low = estimate_latency_impact(frame, queries_per_day=1000, working_days_per_year=250)
    high = estimate_latency_impact(frame, queries_per_day=2000, working_days_per_year=250)
    assert high["estimated_hours_saved_per_year"] == pytest.approx(
        low["estimated_hours_saved_per_year"] * 2
    )


def test_plot_writes_figure_with_source(tmp_path: Path):
    frame = load_pilot_metrics(FIXTURE)
    path = plot_latency_comparison(frame, tmp_path / "latency.png", source_label="fixture")
    assert path.exists() and path.stat().st_size > 0


def test_run_impact_report_writes_artifacts(tmp_path: Path):
    paths = run_impact_report(
        metrics_path=FIXTURE,
        study_path=STUDY,
        figures_dir=tmp_path / "figures",
        tables_dir=tmp_path / "tables",
        assumptions={"queries_per_day": 5000},
    )
    for key in ("figure", "estimate_json", "estimate_csv"):
        assert paths[key].exists()
    payload = json.loads(paths["estimate_json"].read_text(encoding="utf-8"))
    assert payload["assumptions"]["queries_per_day"] == 5000
    assert payload["kind"] == "estimate"


def test_missing_metric_raises():
    frame = load_pilot_metrics(FIXTURE).drop(columns=["query_latency_ms"])
    with pytest.raises(ImpactEstimationError, match="métrica ausente"):
        estimate_latency_impact(frame)
