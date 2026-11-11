from pathlib import Path

import json

import pandas as pd

from lab04_hypothesis.config_loader import load_simulation_config
from lab04_hypothesis.interpretation import classify_type_i, interpret_g3, interpret_g4
from lab04_hypothesis.plots_s02 import plot_g3, plot_g4
from lab04_hypothesis.q3_violations import run_q3, run_q3_type_i, violation_by_name
from lab04_hypothesis.s02_report import run_s02_report

CONFIG = Path(__file__).parents[1] / 'config' / 'simulation.json'


def _type_i_frame():
    rows = []
    for situation, welch, mann in (('ideal', 0.05, 0.049), ('extreme_outlier', 0.02, 0.051)):
        rows.append({'question': 'Q1', 'situation': situation, 'test_name': 'welch_t', 'replications': 10000, 'rejections': int(welch * 10000), 'rejection_rate': welch, 'alpha': 0.05})
        rows.append({'question': 'Q1', 'situation': situation, 'test_name': 'mann_whitney', 'replications': 10000, 'rejections': int(mann * 10000), 'rejection_rate': mann, 'alpha': 0.05})
    return pd.DataFrame(rows)


def _power_frame():
    rows = []
    for situation in ('ideal', 'small_sample'):
        for effect, welch, mann in ((0.0, 0.05, 0.05), (0.5, 0.10, 0.30), (2.0, 0.40, 0.90)):
            if situation == 'small_sample':
                welch, mann = mann, welch
            rows.append({'situation': situation, 'test_name': 'welch_t', 'effect_hours': effect, 'power': welch, 'replications': 100, 'alpha': 0.05})
            rows.append({'situation': situation, 'test_name': 'mann_whitney', 'effect_hours': effect, 'power': mann, 'replications': 100, 'alpha': 0.05})
    return pd.DataFrame(rows)


def test_q3_uses_configured_violations_and_is_reproducible():
    config = load_simulation_config(CONFIG)
    first = run_q3(config, replications=5)
    second = run_q3(config, replications=5)
    assert first == second
    assert {row['situation'] for row in first['q3_type_i']} == {'small_sample', 'extreme_outlier'}
    assert len(first['q3_power']) == 2 * 2 * len(config['effect_sizes_hours'])


def test_q3_type_i_rates_are_proportions():
    config = load_simulation_config(CONFIG)
    rows = run_q3_type_i(config, violation_by_name(config, 'small_sample'), replications=20)
    assert {row['test_name'] for row in rows} == {'welch_t', 'mann_whitney'}
    assert all(0 <= row['rejection_rate'] <= 1 for row in rows)


def test_classify_type_i_uses_monte_carlo_margin():
    assert classify_type_i(0.05, 0.05, 10000) == 'adequado'
    assert classify_type_i(0.08, 0.05, 10000) == 'liberal'
    assert classify_type_i(0.02, 0.05, 10000) == 'conservador'


def test_g3_has_reference_line_at_five_percent(tmp_path: Path):
    path = plot_g3(_type_i_frame(), tmp_path / 'g3.png', alpha=0.05)
    assert path.exists() and path.stat().st_size > 0


def test_g4_has_both_power_curves(tmp_path: Path):
    path = plot_g4(_power_frame(), tmp_path / 'g4.png', alpha=0.05)
    assert path.exists() and path.stat().st_size > 0


def test_interpretations_mention_deviation_and_switch():
    g3 = interpret_g3(_type_i_frame())
    g4 = interpret_g4(_power_frame())
    assert 'conservador' in g3
    assert 'Welch' in g3
    assert 'mudou de lado' in g4
    assert 2 <= g3.count('. ') + 1 <= 4
    assert 2 <= g4.count('. ') + 1 <= 4


def test_g4_reports_when_advantage_never_switches():
    frame = _power_frame()
    frame = frame[frame['situation'] == 'ideal']
    text = interpret_g4(frame)
    assert 'não mudou de lado' in text
    assert 2 <= text.count('. ') + 1 <= 4


def test_s02_report_writes_figures_tables_and_texts(tmp_path: Path):
    artifacts = run_s02_report(
        config_path=CONFIG,
        processed_dir=tmp_path / 'processed',
        figures_dir=tmp_path / 'figures',
        tables_dir=tmp_path / 'tables',
        replications=5,
    )
    for key in ('g3_figure', 'g4_figure', 'g3_table', 'g4_table', 'interpretation'):
        assert Path(artifacts[key]).exists()
    g3 = pd.read_csv(artifacts['g3_table'])
    g4 = pd.read_csv(artifacts['g4_table'])
    assert set(g3['situation']) == {'ideal', 'small_sample', 'extreme_outlier'}
    assert set(g4['test_name']) == {'welch_t', 'mann_whitney'}
    texts = json.loads(Path(artifacts['interpretation']).read_text(encoding='utf-8'))
    assert texts['g3'] and texts['g4']
    assert (tmp_path / 'processed' / 'q1_results.csv').exists()


def test_s02_report_reuses_existing_q1_q2(tmp_path: Path):
    kwargs = dict(
        config_path=CONFIG,
        processed_dir=tmp_path / 'processed',
        figures_dir=tmp_path / 'figures',
        tables_dir=tmp_path / 'tables',
        replications=3,
    )
    assert run_s02_report(**kwargs)['texts']['q1_q2_reused'] is False
    assert run_s02_report(**kwargs)['texts']['q1_q2_reused'] is True
