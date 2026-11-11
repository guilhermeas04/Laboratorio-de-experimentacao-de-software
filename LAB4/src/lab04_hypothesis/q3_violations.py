"""Q3 do LAB04S02: erro tipo I e poder sob violação de pressupostos."""

from __future__ import annotations

from typing import Any

import numpy as np

from .hypothesis_tests import run_both_tests
from .simulate import simulate_dataset
from .simulation_runner import _samples, run_q1, run_q2

IDEAL = "ideal"


def violation_by_name(config: dict[str, Any], name: str) -> dict[str, Any]:
    for violation in config.get("violations", []):
        if violation["name"] == name:
            return violation
    raise ValueError(f"violação não configurada: {name}")


def _situation_offset(config: dict[str, Any], name: str) -> int:
    names = [violation["name"] for violation in config.get("violations", [])]
    return 1000 * (names.index(name) + 1)


def run_q3_type_i(
    config: dict[str, Any],
    violation: dict[str, Any],
    *,
    replications: int | None = None,
) -> list[dict[str, Any]]:
    reps = int(replications or config["replications"])
    seed = int(config["random_seed"]) + _situation_offset(config, violation["name"])
    rng = np.random.default_rng(seed)
    counts = {name: 0 for name in config["tests"]}
    for _ in range(reps):
        frame = simulate_dataset(config, under_null=True, rng=rng, violation=violation)
        bot, human = _samples(frame)
        for result in run_both_tests(bot, human, alternative=config["alternative"], alpha=config["alpha"]):
            counts[result.test_name] += int(result.reject_null)
    return [
        {
            "question": "Q3",
            "situation": violation["name"],
            "test_name": name,
            "replications": reps,
            "rejections": counts[name],
            "rejection_rate": counts[name] / reps,
            "alpha": config["alpha"],
        }
        for name in config["tests"]
    ]


def run_q3_power(
    config: dict[str, Any],
    violation: dict[str, Any],
    *,
    replications: int | None = None,
) -> list[dict[str, Any]]:
    reps = int(replications or config["replications"])
    offset = _situation_offset(config, violation["name"])
    rows = []
    for effect in config["effect_sizes_hours"]:
        seed = int(config["random_seed"]) + offset + int(round(effect * 1000)) + 100
        rng = np.random.default_rng(seed)
        counts = {name: 0 for name in config["tests"]}
        for _ in range(reps):
            frame = simulate_dataset(
                config,
                under_null=True,
                effect_hours=float(effect),
                rng=rng,
                violation=violation,
            )
            bot, human = _samples(frame)
            for result in run_both_tests(bot, human, alternative=config["alternative"], alpha=config["alpha"]):
                counts[result.test_name] += int(result.reject_null)
        for name in config["tests"]:
            rows.append(
                {
                    "question": "Q3",
                    "situation": violation["name"],
                    "test_name": name,
                    "effect_hours": float(effect),
                    "replications": reps,
                    "rejections": counts[name],
                    "power": counts[name] / reps,
                    "alpha": config["alpha"],
                }
            )
    return rows


def run_q3(config: dict[str, Any], *, replications: int | None = None) -> dict[str, list[dict[str, Any]]]:
    type_i: list[dict[str, Any]] = []
    power: list[dict[str, Any]] = []
    for violation in config.get("violations", []):
        type_i.extend(run_q3_type_i(config, violation, replications=replications))
        power.extend(run_q3_power(config, violation, replications=replications))
    return {"q3_type_i": type_i, "q3_power": power}


def collect_all_situations(
    config: dict[str, Any],
    *,
    replications: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Reúne a situação ideal (Q1/Q2) e as violações (Q3) no mesmo formato."""

    q3 = run_q3(config, replications=replications)
    return {
        "type_i": run_q1(config, replications=replications) + q3["q3_type_i"],
        "power": run_q2(config, replications=replications) + q3["q3_power"],
    }
