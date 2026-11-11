"""Executa Q3 e gera G3/G4 a partir dos resultados de Q1/Q2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .config_loader import load_simulation_config
from .interpretation import interpret_g3, interpret_g4
from .plots_s02 import plot_g3, plot_g4
from .q3_violations import run_q3
from .simulation_runner import run_q1, run_q2, write_results

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "simulation.json"
DEFAULT_PROCESSED = ROOT / "data" / "processed"
DEFAULT_FIGURES = ROOT / "reports" / "figures"
DEFAULT_TABLES = ROOT / "reports" / "tables"


def load_or_run_q1_q2(
    config: dict[str, Any],
    processed_dir: Path,
    *,
    replications: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Reaproveita q1/q2_results.csv quando batem com as repetições pedidas."""

    reps = int(replications or config["replications"])
    q1_path = processed_dir / "q1_results.csv"
    q2_path = processed_dir / "q2_results.csv"
    if q1_path.exists() and q2_path.exists():
        q1 = pd.read_csv(q1_path)
        q2 = pd.read_csv(q2_path)
        if (q1["replications"] == reps).all() and (q2["replications"] == reps).all():
            return q1, q2, True

    results = {"q1": run_q1(config, replications=reps), "q2": run_q2(config, replications=reps)}
    write_results(results, processed_dir)
    return pd.DataFrame(results["q1"]), pd.DataFrame(results["q2"]), False


def run_s02_report(
    *,
    config_path: Path = DEFAULT_CONFIG,
    processed_dir: Path = DEFAULT_PROCESSED,
    figures_dir: Path = DEFAULT_FIGURES,
    tables_dir: Path = DEFAULT_TABLES,
    replications: int | None = None,
) -> dict[str, Any]:
    config = load_simulation_config(config_path)
    processed_dir = Path(processed_dir)
    figures_dir = Path(figures_dir)
    tables_dir = Path(tables_dir)
    for directory in (processed_dir, figures_dir, tables_dir):
        directory.mkdir(parents=True, exist_ok=True)

    q1, q2, reused = load_or_run_q1_q2(config, processed_dir, replications=replications)
    q3 = run_q3(config, replications=replications)
    q3_type_i = pd.DataFrame(q3["q3_type_i"])
    q3_power = pd.DataFrame(q3["q3_power"])
    q3_type_i.to_csv(processed_dir / "q3_type_i_results.csv", index=False)
    q3_power.to_csv(processed_dir / "q3_power_results.csv", index=False)

    type_i = pd.concat([q1, q3_type_i], ignore_index=True)
    power = pd.concat([q2, q3_power], ignore_index=True)
    g3_table = tables_dir / "g3_type_i_error.csv"
    g4_table = tables_dir / "g4_power.csv"
    type_i.to_csv(g3_table, index=False)
    power.to_csv(g4_table, index=False)

    alpha = float(config["alpha"])
    g3_figure = plot_g3(type_i, figures_dir / "g3_type_i_error.png", alpha=alpha)
    g4_figure = plot_g4(power, figures_dir / "g4_power.png", alpha=alpha)

    texts = {
        "g3": interpret_g3(type_i),
        "g4": interpret_g4(power),
        "q3_situations": [violation["name"] for violation in config.get("violations", [])],
        "replications": int(type_i["replications"].iloc[0]),
        "alpha": alpha,
        "random_seed": int(config["random_seed"]),
        "q1_q2_reused": reused,
    }
    interpretation_path = tables_dir / "g3_g4_interpretation.json"
    interpretation_path.write_text(json.dumps(texts, indent=2, ensure_ascii=False), encoding="utf-8")
    (processed_dir / "q3_summary.json").write_text(
        json.dumps(
            {"type_i": q3["q3_type_i"], "power": q3["q3_power"], "interpretation": texts},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "g3_figure": g3_figure,
        "g4_figure": g4_figure,
        "g3_table": g3_table,
        "g4_table": g4_table,
        "interpretation": interpretation_path,
        "texts": texts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Executa Q3 e gera G3/G4 do LAB04S02.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--replications", type=int, default=None)
    args = parser.parse_args(argv)
    artifacts = run_s02_report(config_path=args.config, replications=args.replications)
    for name in ("g3_figure", "g4_figure", "g3_table", "g4_table", "interpretation"):
        print(f"{name}: {artifacts[name]}")
    print(f"\nG3: {artifacts['texts']['g3']}\n\nG4: {artifacts['texts']['g4']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
