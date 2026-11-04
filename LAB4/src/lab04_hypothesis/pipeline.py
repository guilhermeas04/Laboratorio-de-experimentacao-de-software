"""Pipeline S01: simulacao exemplo, testes e figuras G1/G2."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .config_loader import load_simulation_config
from .hypothesis_tests import run_both_tests
from .plots import null_welch_statistics, plot_g1, plot_g2
from .simulate import simulate_calibrated_example

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "simulation.json"
DEFAULT_REAL = ROOT / "data" / "raw" / "pr_merge_time.csv"
DEFAULT_PROCESSED = ROOT / "data" / "processed"
DEFAULT_FIGURES = ROOT / "reports" / "figures"
DEFAULT_TABLES = ROOT / "reports" / "tables"
DEFAULT_DASHBOARD = ROOT / "dashboard" / "index.html"


def load_real_data(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"group", "duration_hours"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"colunas ausentes nos dados reais: {sorted(missing)}")
    return frame


def write_dashboard(path: Path, example_rows: list[dict], g1: Path, g2: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_html = "\n".join(
        f"<tr><td>{row['test_name']}</td><td>{row['statistic']:.4f}</td>"
        f"<td>{row['p_value']:.4f}</td><td>{row['effect_size']:.4f}</td>"
        f"<td>{'rejeita H0' if row['reject_null'] else 'nao rejeita H0'}</td></tr>"
        for row in example_rows
    )
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>LAB04 — Dashboard S01</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 960px; color: #222; }}
    h1, h2 {{ font-family: Helvetica, Arial, sans-serif; }}
    img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }}
    th {{ background: #f3f3f3; }}
  </style>
</head>
<body>
  <h1>LAB04S01 — Testes, simulacao e graficos G1/G2</h1>
  <h2>1. Cenario</h2>
  <p>P1: tempo ate o merge de PRs de bot versus humanos. H0: distribuicoes iguais.
  H1: distribuicoes diferem. Testes bicaudais: Welch e Mann-Whitney.</p>
  <h2>2. Os dados — G1</h2>
  <p>Os histogramas comparam a amostra real (30 por grupo) com uma amostra
  simulada calibrada nas medianas e dispersoes observadas.</p>
  <img src="{_rel(path, g1)}" alt="Grafico G1" />
  <h2>3. Como os testes funcionam — G2</h2>
  <p>A distribuicao da estatistica t de Welch sob H0 foi obtida por simulacao
  com semente fixa. A faixa sombreada marca a regiao de rejeicao para alpha=0,05
  e a linha tracejada mostra um exemplo com seu p-valor.</p>
  <img src="{_rel(path, g2)}" alt="Grafico G2" />
  <h2>4. Exemplo simulado</h2>
  <table>
    <thead><tr><th>Teste</th><th>Estatistica</th><th>p-valor</th><th>Efeito</th><th>Conclusao</th></tr></thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return path


def _rel(from_path: Path, target: Path) -> str:
    return os.path.relpath(Path(target).resolve(), start=from_path.parent.resolve()).replace(os.sep, "/")


def run_pipeline(
    *,
    config_path: Path = DEFAULT_CONFIG,
    real_path: Path = DEFAULT_REAL,
    processed_dir: Path = DEFAULT_PROCESSED,
    figures_dir: Path = DEFAULT_FIGURES,
    tables_dir: Path = DEFAULT_TABLES,
    dashboard_path: Path = DEFAULT_DASHBOARD,
    null_replications: int | None = None,
) -> dict:
    config = load_simulation_config(config_path)
    real = load_real_data(real_path)
    rng = np.random.default_rng(int(config["random_seed"]))
    simulated = simulate_calibrated_example(config, rng=rng)

    bot = simulated.loc[simulated["group"] == "bot", "duration_hours"].to_numpy()
    human = simulated.loc[simulated["group"] == "human", "duration_hours"].to_numpy()
    example_results = run_both_tests(
        bot,
        human,
        alternative=config["alternative"],
        alpha=float(config["alpha"]),
    )

    processed_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    simulated_path = processed_dir / "simulated_example.csv"
    simulated.to_csv(simulated_path, index=False)

    example_rows = [result.to_dict() for result in example_results]
    example_table = tables_dir / "example_tests.csv"
    pd.DataFrame(example_rows).to_csv(example_table, index=False)
    example_json = processed_dir / "example_tests.json"
    example_json.write_text(json.dumps(example_rows, indent=2), encoding="utf-8")

    g1_path = figures_dir / "g1_histograms.png"
    plot_g1(real, simulated, g1_path)

    reps = null_replications if null_replications is not None else min(int(config["replications"]), 2000)
    null_stats, example_stat, example_p = null_welch_statistics(config, replications=reps)
    g2_path = figures_dir / "g2_null_distribution.png"
    plot_g2(null_stats, example_stat, example_p, float(config["alpha"]), g2_path)

    null_summary = {
        "replications": reps,
        "alpha": float(config["alpha"]),
        "critical_low": float(np.quantile(null_stats, float(config["alpha"]) / 2)),
        "critical_high": float(np.quantile(null_stats, 1 - float(config["alpha"]) / 2)),
        "example_statistic": example_stat,
        "example_p_value": example_p,
    }
    (processed_dir / "g2_null_summary.json").write_text(json.dumps(null_summary, indent=2), encoding="utf-8")

    dashboard = write_dashboard(dashboard_path, example_rows, g1_path, g2_path)
    return {
        "simulated_example": str(simulated_path),
        "example_tests": str(example_table),
        "g1": str(g1_path),
        "g2": str(g2_path),
        "dashboard": str(dashboard),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline LAB04S01: testes, simulacao e G1/G2")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--real-data", type=Path, default=DEFAULT_REAL)
    parser.add_argument("--null-replications", type=int, default=None)
    args = parser.parse_args(argv)
    artifacts = run_pipeline(
        config_path=args.config,
        real_path=args.real_data,
        null_replications=args.null_replications,
    )
    print("OK: pipeline LAB04S01 concluida")
    for name, path in artifacts.items():
        print(f"- {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
