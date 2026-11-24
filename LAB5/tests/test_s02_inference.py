from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lab05_real_software.s02_inference import (
    PairedInferenceError,
    build_pairs,
    holm_adjust,
    paired_effect_size,
    paired_t_analysis,
    practical_relevance,
    run_paired_inference,
)

ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "processed" / "lab05s02-20261121-01_validated.csv"
CONFIG = ROOT / "config" / "collection-s02.json"


def _pairs(values_a, values_b) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "block": list(range(1, len(values_a) + 1)),
            "value_a": values_a,
            "value_b": values_b,
            "difference_a_minus_b": np.asarray(values_a, dtype=float) - np.asarray(values_b, dtype=float),
        }
    )


def test_incomplete_pairs_are_excluded_from_primary_contrast():
    frame = pd.DataFrame(
        {
            "campaign_id": ["c"] * 5,
            "block": [1, 1, 2, 2, 3],
            "position": [1, 2, 1, 2, 1],
            "software_version": ["15.20", "17.12", "15.20", "17.12", "15.20"],
            "scenario": ["customer_total"] * 5,
            "query_latency_ms": [1.0, 0.8, 1.1, np.nan, 1.2],
        }
    )
    pairs = build_pairs(frame, scenario="customer_total", metric="query_latency_ms", versions=["15.20", "17.12"])
    assert list(pairs["block"]) == [1]
    result = paired_t_analysis(pairs, metric="query_latency_ms")
    assert result["n_pairs"] == 1
    assert result["inference_status"] == "insufficient"


def test_zero_variance_marks_inference_insufficient():
    pairs = _pairs([1.0, 1.0, 1.0], [0.5, 0.5, 0.5])
    result = paired_t_analysis(pairs, metric="query_latency_ms")
    assert result["inference_status"] == "insufficient"
    assert result["effect_size"]["defined"] is False


def test_small_sample_effect_size_undefined_below_two_pairs():
    effect = paired_effect_size(np.array([0.1]))
    assert effect["defined"] is False
    assert effect["cohens_dz"] is None


def test_two_pairs_preserve_effect_size_without_t_decision():
    result = paired_t_analysis(_pairs([1.0, 2.0], [0.5, 1.0]), metric="query_latency_ms")
    assert result["inference_status"] == "insufficient"
    assert result["p_value"] is None
    assert result["effect_size"]["defined"] is True


def test_practical_relevance_uses_predefined_threshold():
    relevance = practical_relevance(
        mean_version_a=1.0,
        mean_difference=0.12,
        metric="query_latency_ms",
        minimum_relative_reduction=0.1,
    )
    assert relevance["interpretation"] == "threshold_met"
    assert relevance["observed_relative_change_percent"] == pytest.approx(12.0)


def test_holm_adjustment_controls_family_wise_error():
    adjusted = holm_adjust([0.01, 0.04, None, 0.03])
    assert adjusted[2] is None
    assert adjusted[0] == pytest.approx(0.03)
    assert adjusted[3] == pytest.approx(0.06)
    assert adjusted[1] == pytest.approx(0.06)


def test_run_paired_inference_on_real_dataset(tmp_path: Path):
    paths = run_paired_inference(
        dataset_path=DATASET,
        config_path=CONFIG,
        tables_dir=tmp_path / "tables",
        docs_dir=tmp_path / "docs",
    )
    for key in ("pairs", "primary", "secondary", "summary", "docs"):
        assert paths[key].exists()
    primary = json.loads(paths["primary"].read_text(encoding="utf-8"))
    assert primary["role"] == "primary"
    assert primary["scenario"] == "customer_total"
    assert primary["metric"] == "query_latency_ms"
    assert primary["n_pairs"] == 24
    assert primary["p_value"] == pytest.approx(0.00264458)
    assert primary["inference_status"] == "assumption_warning"
    assert primary["reject_null"] is None
    assert primary["effect_size"]["defined"] is True
    assert "practical_relevance" in primary
    secondary = pd.read_csv(paths["secondary"])
    assert "p_value_holm" in secondary.columns
    assert len(secondary) > 0


def test_missing_metric_raises():
    frame = pd.DataFrame(
        {
            "block": [1, 1],
            "position": [1, 2],
            "software_version": ["15.20", "17.12"],
            "scenario": ["customer_total", "customer_total"],
        }
    )
    with pytest.raises(PairedInferenceError, match="métrica ausente"):
        build_pairs(frame, scenario="customer_total", metric="query_latency_ms", versions=["15.20", "17.12"])
