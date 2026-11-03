from pathlib import Path
import json
from typing import Any

REQUIRED_KEYS = {'scenario','question','tests','alternative','alpha','random_seed','replications','sample_sizes','effect_sizes_hours','parameters'}

def load_simulation_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding='utf-8') as file:
        config = json.load(file)
    validate_simulation_config(config)
    return config

def validate_simulation_config(config: dict[str, Any]) -> None:
    missing = REQUIRED_KEYS - config.keys()
    if missing:
        raise ValueError(f'chaves obrigatorias ausentes: {sorted(missing)}')
    if config['scenario'] != 'P1':
        raise ValueError('o cenario configurado deve ser P1')
    if set(config['tests']) != {'welch_t', 'mann_whitney'}:
        raise ValueError('P1 deve usar welch_t e mann_whitney')
    if config['alternative'] != 'two-sided':
        raise ValueError('a comparacao deve ser bicaudal')
    if not 0 < config['alpha'] < 1:
        raise ValueError('alpha deve estar entre 0 e 1')
    if config['random_seed'] < 0 or config['replications'] <= 0:
        raise ValueError('semente e repeticoes devem ser positivas')
    if len(config['effect_sizes_hours']) < 5 or config['effect_sizes_hours'][0] != 0:
        raise ValueError('sao necessarios cinco efeitos comecando em zero')
    for group in ('bot', 'human'):
        if config['sample_sizes'][group] <= 0 or config['parameters'][group]['sigma_log'] <= 0:
            raise ValueError(f'parametros invalidos para o grupo {group}')
