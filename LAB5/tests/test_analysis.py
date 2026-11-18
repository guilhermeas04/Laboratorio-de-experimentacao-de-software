from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lab05_real_software.analysis import (
    PilotAnalysisError,
    available_metrics,
    descriptive_stats,
    effect_sizes,
    load_pilot_metrics,
    run_pilot_analysis,
)

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "pilot_metrics.csv"
STUDY = ROOT / "config" / "study.json"


def test_load_preserves_missing_as_nan_not_zero():
    frame = load_pilot_metrics(FIXTURE)
    assert frame["query_latency_ms"].isna().sum() == 1
    assert frame["throughput_queries_per_second"].isna().sum() == 1
    # o valor ausente não pode ter virado 0
    assert not ((frame["query_latency_ms"] == 0) & frame["query_latency_ms"].isna()).any()
    assert pd.isna(frame.loc[frame["software_version"].astype(str) == "15", "query_latency_ms"].iloc[2])


def test_descriptive_stats_count_missing_explicitly():
    frame = load_pilot_metrics(FIXTURE)
    stats = descriptive_stats(frame, ["query_latency_ms"])
    row_15 = stats.loc[stats["software_version"] == "15"].iloc[0]
    assert row_15["n"] == 5
    assert row_15["n_observed"] == 4
    assert row_15["n_missing"] == 1
    assert row_15["mean"] > 0
    assert not np.isnan(row_15["median"])


def test_effect_size_ignores_missing_and_compares_versions():
    frame = load_pilot_metrics(FIXTURE)
    effects = effect_sizes(frame, ["query_latency_ms"], baseline_version="15", treatment_version="17")
    row = effects.iloc[0]
    assert row["n_baseline"] == 4
    assert row["n_treatment"] == 5
    assert row["mean_treatment"] < row["mean_baseline"]
    assert row["cohens_d"] > 0
    assert row["direction_hint"] == "favoravel_17"


def test_run_pilot_analysis_writes_tables(tmp_path: Path):
    paths = run_pilot_analysis(
        metrics_path=FIXTURE,
        study_path=STUDY,
        tables_dir=tmp_path / "tables",
    )
    for key in ("descriptive", "effect_sizes", "summary"):
        assert paths[key].exists()
    descriptive = pd.read_csv(paths["descriptive"])
    assert set(descriptive["metric"]) >= {"query_latency_ms", "cpu_percent"}
    assert "n_missing" in descriptive.columns


def test_missing_metrics_file_raises():
    with pytest.raises(PilotAnalysisError, match="não encontrado"):
        load_pilot_metrics(ROOT / "tests" / "fixtures" / "ausente.csv")


def test_available_metrics_filters_present_columns():
    frame = pd.DataFrame({"software_version": ["15"], "query_latency_ms": [1.0]})
    assert available_metrics(frame) == ["query_latency_ms"]
