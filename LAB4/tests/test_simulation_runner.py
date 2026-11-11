from pathlib import Path

import numpy as np

from lab04_hypothesis.config_loader import load_simulation_config
from lab04_hypothesis.simulation_runner import run_q1, run_q2, run_all, write_results

CONFIG = Path(__file__).parents[1] / 'config' / 'simulation.json'


def test_q1_is_reproducible_and_has_both_tests():
    config = load_simulation_config(CONFIG)
    first = run_q1(config, replications=25)
    second = run_q1(config, replications=25)
    assert first == second
    assert {row['test_name'] for row in first} == {'welch_t', 'mann_whitney'}
    assert all(0 <= row['rejection_rate'] <= 1 for row in first)


def test_q2_contains_five_effects_and_both_tests():
    config = load_simulation_config(CONFIG)
    rows = run_q2(config, replications=10)
    assert len(rows) == 10
    assert {row['effect_hours'] for row in rows} == {0.0, 0.25, 0.5, 1.0, 2.0}
    assert {row['test_name'] for row in rows} == {'welch_t', 'mann_whitney'}


def test_results_are_written(tmp_path: Path):
    config = load_simulation_config(CONFIG)
    paths = write_results(run_all(config, replications=2), tmp_path)
    assert paths['q1'].exists()
    assert paths['q2'].exists()
    assert (tmp_path / 'q1_q2_summary.json').exists()
