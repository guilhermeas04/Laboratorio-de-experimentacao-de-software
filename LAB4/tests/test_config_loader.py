from pathlib import Path
import pytest
from lab04_hypothesis.config_loader import load_simulation_config, validate_simulation_config

CONFIG = Path(__file__).parents[1] / 'config' / 'simulation.json'

def test_simulation_config_is_loadable_and_reproducible():
    config = load_simulation_config(CONFIG)
    assert config['random_seed'] == 42
    assert config['replications'] == 10000
    assert config['effect_sizes_hours'][0] == 0

def test_invalid_config_rejects_non_two_sided_comparison():
    config = load_simulation_config(CONFIG)
    config['alternative'] = 'greater'
    with pytest.raises(ValueError, match='bicaudal'):
        validate_simulation_config(config)
