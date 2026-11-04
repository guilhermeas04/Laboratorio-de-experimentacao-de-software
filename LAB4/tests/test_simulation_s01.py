from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from lab04_hypothesis.config_loader import load_simulation_config
from lab04_hypothesis.hypothesis_tests import mann_whitney_test, run_both_tests, welch_t_test
from lab04_hypothesis.pipeline import run_pipeline
from lab04_hypothesis.simulate import simulate_calibrated_example, simulate_dataset

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "config" / "simulation.json"
REAL = ROOT / "data" / "raw" / "pr_merge_time.csv"


def test_welch_and_mannwhitney_return_expected_fields():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, size=30)
    b = rng.normal(0.5, 1.2, size=30)
    results = run_both_tests(a, b, alpha=0.05)
    names = {item.test_name for item in results}
    assert names == {"welch_t", "mann_whitney"}
    for item in results:
        assert 0 <= item.p_value <= 1
        assert item.alpha == 0.05


def test_simulation_is_reproducible_with_fixed_seed():
    config = load_simulation_config(CONFIG)
    first = simulate_calibrated_example(config, rng=np.random.default_rng(42))
    second = simulate_calibrated_example(config, rng=np.random.default_rng(42))
    pd.testing.assert_frame_equal(first, second)
    assert set(first["group"]) == {"bot", "human"}
    assert len(first) == config["sample_sizes"]["bot"] + config["sample_sizes"]["human"]


def test_null_simulation_keeps_groups_exchangeable_on_parameters():
    config = load_simulation_config(CONFIG)
    frame = simulate_dataset(config, under_null=True, effect_hours=0.0, rng=np.random.default_rng(7))
    assert frame["group"].value_counts().to_dict() == {"bot": 30, "human": 30}


def test_effect_shift_increases_human_mean():
    config = load_simulation_config(CONFIG)
    base = simulate_dataset(config, under_null=True, effect_hours=0.0, rng=np.random.default_rng(3))
    shifted = simulate_dataset(config, under_null=True, effect_hours=2.0, rng=np.random.default_rng(3))
    base_human = base.loc[base["group"] == "human", "duration_hours"].mean()
    shifted_human = shifted.loc[shifted["group"] == "human", "duration_hours"].mean()
    assert shifted_human > base_human


def test_pipeline_writes_g1_g2_and_example_outputs(tmp_path: Path):
    artifacts = run_pipeline(
        config_path=CONFIG,
        real_path=REAL,
        processed_dir=tmp_path / "processed",
        figures_dir=tmp_path / "figures",
        tables_dir=tmp_path / "tables",
        dashboard_path=tmp_path / "dashboard" / "index.html",
        null_replications=50,
    )
    for key in ("simulated_example", "example_tests", "g1", "g2", "dashboard"):
        assert Path(artifacts[key]).exists()
    table = pd.read_csv(artifacts["example_tests"])
    assert set(table["test_name"]) == {"welch_t", "mann_whitney"}


def test_identical_samples_do_not_reject():
    sample = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    welch = welch_t_test(sample, sample.copy())
    mann = mann_whitney_test(sample, sample.copy())
    assert welch.reject_null is False
    assert mann.reject_null is False
