"""Simulações Q1 e Q2 do LAB04S02."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config_loader import load_simulation_config
from .hypothesis_tests import run_both_tests
from .simulate import simulate_dataset


def _samples(frame):
    return (
        frame.loc[frame["group"] == "bot", "duration_hours"].to_numpy(),
        frame.loc[frame["group"] == "human", "duration_hours"].to_numpy(),
    )


def run_q1(config: dict[str, Any], *, replications: int | None = None) -> list[dict[str, Any]]:
    """Estima o erro tipo I com H0 verdadeira."""
    reps = int(replications or config["replications"])
    rng = np.random.default_rng(int(config["random_seed"]))
    counts = {name: 0 for name in config["tests"]}
    for _ in range(reps):
        bot, human = _samples(simulate_dataset(config, under_null=True, rng=rng))
        for result in run_both_tests(bot, human, alternative=config["alternative"], alpha=config["alpha"]):
            counts[result.test_name] += int(result.reject_null)
    return [
        {
            "question": "Q1",
            "situation": "ideal",
            "test_name": name,
            "replications": reps,
            "rejections": counts[name],
            "rejection_rate": counts[name] / reps,
            "alpha": config["alpha"],
        }
        for name in config["tests"]
    ]


def run_q2(config: dict[str, Any], *, replications: int | None = None) -> list[dict[str, Any]]:
    """Estima o poder para os efeitos definidos na configuração."""
    reps = int(replications or config["replications"])
    rows = []
    for effect in config["effect_sizes_hours"]:
        rng = np.random.default_rng(int(config["random_seed"]) + int(round(effect * 1000)) + 100)
        counts = {name: 0 for name in config["tests"]}
        for _ in range(reps):
            bot, human = _samples(
                simulate_dataset(
                    config,
                    under_null=True,
                    effect_hours=float(effect),
                    rng=rng,
                )
            )
            for result in run_both_tests(bot, human, alternative=config["alternative"], alpha=config["alpha"]):
                counts[result.test_name] += int(result.reject_null)
        for name in config["tests"]:
            rows.append(
                {
                    "question": "Q2",
                    "situation": "ideal",
                    "test_name": name,
                    "effect_hours": float(effect),
                    "replications": reps,
                    "rejections": counts[name],
                    "power": counts[name] / reps,
                    "alpha": config["alpha"],
                }
            )
    return rows


def run_all(config: dict[str, Any], *, replications: int | None = None) -> dict[str, list[dict[str, Any]]]:
    return {"q1": run_q1(config, replications=replications), "q2": run_q2(config, replications=replications)}


def write_results(results: dict[str, list[dict[str, Any]]], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, rows in results.items():
        path = output_dir / f"{name}_results.csv"
        import csv
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        paths[name] = path
    (output_dir / "q1_q2_summary.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Executa Q1 e Q2 do LAB04S02.")
    parser.add_argument("--config", type=Path, default=Path("LAB4/config/simulation.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("LAB4/data/processed"))
    parser.add_argument("--replications", type=int, default=None)
    args = parser.parse_args(argv)
    config = load_simulation_config(args.config)
    paths = write_results(run_all(config, replications=args.replications), args.output_dir)
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
