from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lab05_real_software.s02_descriptive import (
    CompleteAnalysisError,
    complete_pairs_by_block,
    descriptive_by_version_scenario,
    load_validated_dataset,
    plot_metric_by_scenario,
    run_complete_descriptive,
)

ROOT = Path(__file__).parents[1]
REAL_DATASET = ROOT / "data" / "processed" / "lab05s02-20261121-01_validated.csv"


def _tiny_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "campaign_id": ["camp-x"] * 5,
            "block": [1, 1, 2, 2, 3],
            "position": [1, 2, 1, 2, 1],
            "software_version": ["15.20", "17.12", "15.20", "17.12", "15.20"],
            "scenario": ["customer_total"] * 5,
            "execution_id": ["e1", "e1", "e2", "e2", "e3"],
            "round_id": ["r1", "r2", "r3", "r4", "r5"],
            "source": [
                "rounds/a.json",
                "rounds/b.json",
                "rounds/c.json",
                "rounds/d.json",
                "rounds/e.json",
            ],
            "query_latency_ms": [1.0, 0.8, np.nan, 0.9, 1.2],
            "throughput_queries_per_second": [100.0, 120.0, 110.0, np.nan, 90.0],
            "cpu_percent": [50.0, 48.0, 52.0, 47.0, 55.0],
            "memory_mb": [80.0, 81.0, 79.0, 82.0, 78.0],
        }
    )


def test_load_validated_dataset_keeps_version_as_text():
    frame = load_validated_dataset(REAL_DATASET)
    assert str(frame["software_version"].dtype) == "string"
    assert set(frame["software_version"].unique()) == {"15.20", "17.12"}
    assert "block" in frame.columns
    assert "source" in frame.columns


def test_descriptive_counts_missing_and_small_groups():
    stats = descriptive_by_version_scenario(_tiny_frame(), ["query_latency_ms"])
    row_15 = stats.loc[stats["software_version"] == "15.20"].iloc[0]
    assert row_15["n"] == 3
    assert row_15["n_observed"] == 2
    assert row_15["n_missing"] == 1
    assert row_15["mean"] == pytest.approx(1.1)


def test_complete_pairs_preserve_block_and_detect_incomplete():
    pairs = complete_pairs_by_block(_tiny_frame(), ["query_latency_ms"])
    assert set(pairs["block"].dropna().astype(int)) >= {1, 2, 3}
    complete = pairs.loc[pairs["block"] == 1].iloc[0]
    incomplete = pairs.loc[pairs["block"] == 2].iloc[0]
    lonely = pairs.loc[pairs["block"] == 3].iloc[0]
    assert bool(complete["pair_complete"]) is True
    assert bool(incomplete["pair_complete"]) is False
    assert bool(lonely["pair_complete"]) is False
    assert "rounds/a.json" in complete["sources"]


def test_plot_handles_small_groups(tmp_path: Path):
    path = plot_metric_by_scenario(
        _tiny_frame(),
        "query_latency_ms",
        tmp_path / "latency.png",
        dataset_label="fixture",
    )
    assert path.exists() and path.stat().st_size > 0


def test_run_complete_descriptive_writes_artifacts(tmp_path: Path):
    paths = run_complete_descriptive(
        dataset_path=REAL_DATASET,
        tables_dir=tmp_path / "tables",
        figures_dir=tmp_path / "figures",
        docs_dir=tmp_path / "docs",
    )
    for key in (
        "descriptive",
        "complete_pairs",
        "complete_pairs_summary",
        "traceability",
        "metric_catalog",
        "summary",
        "docs",
        "latency_figure",
        "throughput_figure",
    ):
        assert paths[key].exists()

    descriptive = pd.read_csv(paths["descriptive"])
    pairs = pd.read_csv(paths["complete_pairs"])
    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    assert "n_missing" in descriptive.columns
    assert "block" in pairs.columns
    assert summary["n_rows"] == 96
    assert summary["n_blocks"] == 24
    assert (pairs["pair_complete"] == True).all()  # noqa: E712


def test_missing_dataset_raises():
    with pytest.raises(CompleteAnalysisError, match="não encontrado"):
        load_validated_dataset(ROOT / "data" / "processed" / "ausente.csv")
