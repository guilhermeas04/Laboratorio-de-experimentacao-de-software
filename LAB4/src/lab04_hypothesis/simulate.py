"""Geracao de amostras simuladas calibradas no cenario P1."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def generate_group_sample(
    rng: np.random.Generator,
    *,
    n: int,
    mu_log: float,
    sigma_log: float,
    effect_hours: float = 0.0,
    outlier_probability: float = 0.0,
    outlier_multiplier: float = 1.0,
) -> np.ndarray:
    if n <= 0:
        raise ValueError("tamanho amostral deve ser positivo")
    if sigma_log <= 0:
        raise ValueError("sigma_log deve ser positivo")
    sample = rng.lognormal(mean=mu_log, sigma=sigma_log, size=n)
    if effect_hours:
        sample = sample + effect_hours
    sample = np.clip(sample, a_min=1e-9, a_max=None)
    if outlier_probability > 0:
        mask = rng.random(n) < outlier_probability
        sample = sample.copy()
        sample[mask] = sample[mask] * outlier_multiplier
    return sample


def simulate_dataset(
    config: dict[str, Any],
    *,
    effect_hours: float = 0.0,
    under_null: bool = False,
    sample_sizes: dict[str, int] | None = None,
    rng: np.random.Generator | None = None,
    violation: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Gera um conjunto bot/human.

    under_null=True usa os parametros humanos nos dois grupos (H0 verdadeira),
    aplicando apenas o deslocamento effect_hours no grupo human quando > 0.
    """

    seed = int(config["random_seed"])
    generator = rng or np.random.default_rng(seed)
    sizes = sample_sizes or dict(config["sample_sizes"])
    bot_params = dict(config["parameters"]["bot"])
    human_params = dict(config["parameters"]["human"])
    if under_null:
        bot_params = dict(human_params)

    outlier_probability = 0.0
    outlier_multiplier = 1.0
    if violation:
        if "sample_sizes" in violation:
            sizes = dict(violation["sample_sizes"])
        outlier_probability = float(violation.get("outlier_probability", 0.0))
        outlier_multiplier = float(violation.get("outlier_multiplier", 1.0))

    bot = generate_group_sample(
        generator,
        n=int(sizes["bot"]),
        mu_log=float(bot_params["mu_log"]),
        sigma_log=float(bot_params["sigma_log"]),
        outlier_probability=outlier_probability,
        outlier_multiplier=outlier_multiplier,
    )
    human = generate_group_sample(
        generator,
        n=int(sizes["human"]),
        mu_log=float(human_params["mu_log"]),
        sigma_log=float(human_params["sigma_log"]),
        effect_hours=effect_hours,
        outlier_probability=outlier_probability,
        outlier_multiplier=outlier_multiplier,
    )
    rows = [{"group": "bot", "duration_hours": float(value), "effect_hours": effect_hours} for value in bot]
    rows.extend(
        {"group": "human", "duration_hours": float(value), "effect_hours": effect_hours} for value in human
    )
    return pd.DataFrame(rows)


def simulate_calibrated_example(config: dict[str, Any], rng: np.random.Generator | None = None) -> pd.DataFrame:
    """Amostra unica com parametros calibrados nos dados reais (grupos distintos)."""

    return simulate_dataset(config, effect_hours=0.0, under_null=False, rng=rng)
