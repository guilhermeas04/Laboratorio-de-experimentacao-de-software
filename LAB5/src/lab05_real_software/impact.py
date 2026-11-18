"""Visualização e estimativa inicial de impacto do piloto LAB05S01."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analysis import (
    DEFAULT_METRICS,
    DEFAULT_STUDY,
    PilotAnalysisError,
    _observed,
    load_pilot_metrics,
    load_study_config,
    paired_values,
    version_mask,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIGURES = ROOT / "reports" / "figures"
DEFAULT_TABLES = ROOT / "reports" / "tables"

# Premissas explícitas da estimativa inicial (não são medições).
DEFAULT_ASSUMPTIONS = {
    "queries_per_day": 1_000_000,
    "working_days_per_year": 250,
    "metric": "query_latency_ms",
}


class ImpactEstimationError(PilotAnalysisError):
    """Falha ao estimar impacto a partir do piloto."""


def estimate_latency_impact(
    frame: pd.DataFrame,
    *,
    baseline_version: str = "15",
    treatment_version: str = "17",
    metric: str = "query_latency_ms",
    queries_per_day: int = 1_000_000,
    working_days_per_year: int = 250,
) -> dict[str, Any]:
    """Estima impacto operacional se a diferença média de latência se mantiver.

    Trata o resultado como estimativa sob premissas declaradas, não como efeito
    causal medido em produção.
    """

    if metric not in frame.columns:
        raise ImpactEstimationError(f"métrica ausente no piloto: {metric}")

    n_pairs = None
    if "block" in frame:
        pairs = paired_values(frame, metric, baseline_version, treatment_version)
        n_pairs = len(pairs)
        baseline = pairs[baseline_version].to_numpy()
        treatment = pairs[treatment_version].to_numpy()
    else:
        baseline = _observed(frame.loc[version_mask(frame, baseline_version), metric])
        treatment = _observed(frame.loc[version_mask(frame, treatment_version), metric])
    if baseline.size == 0 or treatment.size == 0:
        raise ImpactEstimationError("não há observações suficientes nas duas versões")

    mean_baseline = float(np.mean(baseline))
    mean_treatment = float(np.mean(treatment))
    delta_ms = mean_baseline - mean_treatment
    relative = delta_ms / mean_baseline if mean_baseline else None

    ms_saved_per_day = delta_ms * queries_per_day
    hours_saved_per_year = (ms_saved_per_day * working_days_per_year) / (1000.0 * 60.0 * 60.0)

    return {
        "kind": "estimate",
        "metric": metric,
        "unit": "ms",
        "baseline_version": baseline_version,
        "treatment_version": treatment_version,
        "n_baseline": int(baseline.size),
        "n_treatment": int(treatment.size),
        "n_pairs": n_pairs,
        "mean_baseline_ms": mean_baseline,
        "mean_treatment_ms": mean_treatment,
        "mean_difference_ms": delta_ms,
        "relative_improvement": relative,
        "assumptions": {
            "queries_per_day": queries_per_day,
            "working_days_per_year": working_days_per_year,
        },
        "estimated_hours_saved_per_year": hours_saved_per_year,
        "caveat": (
            "Estimativa inicial do piloto: extrapolação linear da diferença média "
            "de latência sob carga hipotética. As horas representam tempo "
            "acumulado de execução das consultas no servidor. A projeção "
            "depende da carga e da diferença de latência se manterem."
        ),
    }


def plot_latency_comparison(
    frame: pd.DataFrame,
    output_path: Path,
    *,
    metric: str = "query_latency_ms",
    source_label: str = "LAB5/data/interim/pilot_metrics.csv",
) -> Path:
    """Gera gráfico comparativo de latência entre versões."""

    if metric not in frame.columns:
        raise ImpactEstimationError(f"métrica ausente no piloto: {metric}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    versions = [str(v) for v in sorted(frame["software_version"].dropna().unique())]
    data = [_observed(frame.loc[frame["software_version"].astype(str) == version, metric]) for version in versions]
    means = [float(np.mean(values)) if values.size else np.nan for values in data]

    fig, axis = plt.subplots(figsize=(8.5, 5))
    box = axis.boxplot(data, patch_artist=True, widths=0.55)
    axis.set_xticks(range(1, len(versions) + 1), versions)
    colors = ["#4c78a8", "#f58518"]
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.55)
    axis.scatter(range(1, len(versions) + 1), means, color="black", zorder=3, label="média")
    for index, mean in enumerate(means, start=1):
        if not np.isnan(mean):
            axis.annotate(f"{mean:.3f} ms", (index, mean), textcoords="offset points", xytext=(8, 6))

    axis.set_title("Latência de consulta no piloto: PostgreSQL 15 vs 17")
    axis.set_xlabel("Versão do PostgreSQL")
    axis.set_ylabel("Latência da consulta (ms)")
    axis.legend(loc="upper right")
    axis.grid(axis="y", alpha=0.3)
    fig.text(
        0.01,
        0.01,
        f"Fonte: {source_label} | Ausentes excluídos do gráfico | Estimativa piloto LAB05S01",
        fontsize=8,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def run_impact_report(
    *,
    metrics_path: Path = DEFAULT_METRICS,
    study_path: Path = DEFAULT_STUDY,
    figures_dir: Path = DEFAULT_FIGURES,
    tables_dir: Path = DEFAULT_TABLES,
    assumptions: dict[str, Any] | None = None,
) -> dict[str, Path]:
    study = load_study_config(study_path)
    frame = load_pilot_metrics(metrics_path)
    versions = [str(v) for v in study["software"]["versions"]]
    params = dict(DEFAULT_ASSUMPTIONS)
    if assumptions:
        params.update(assumptions)

    estimate = estimate_latency_impact(
        frame,
        baseline_version=versions[0],
        treatment_version=versions[1],
        metric=str(params["metric"]),
        queries_per_day=int(params["queries_per_day"]),
        working_days_per_year=int(params["working_days_per_year"]),
    )

    figures_dir = Path(figures_dir)
    tables_dir = Path(tables_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    figure_path = plot_latency_comparison(
        frame,
        figures_dir / "pilot_latency_comparison.png",
        metric=str(params["metric"]),
        source_label=str(metrics_path),
    )
    estimate_json = tables_dir / "pilot_impact_estimate.json"
    estimate_csv = tables_dir / "pilot_impact_estimate.csv"
    estimate_json.write_text(json.dumps(estimate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pd.DataFrame(
        [
            {
                "field": key,
                "value": value if not isinstance(value, dict) else json.dumps(value, ensure_ascii=False),
            }
            for key, value in estimate.items()
        ]
    ).to_csv(estimate_csv, index=False)

    return {
        "figure": figure_path,
        "estimate_json": estimate_json,
        "estimate_csv": estimate_csv,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Visualização e estimativa de impacto do piloto LAB05S01")
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--study", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES)
    parser.add_argument("--tables-dir", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--queries-per-day", type=int, default=DEFAULT_ASSUMPTIONS["queries_per_day"])
    args = parser.parse_args(argv)
    paths = run_impact_report(
        metrics_path=args.metrics,
        study_path=args.study,
        figures_dir=args.figures_dir,
        tables_dir=args.tables_dir,
        assumptions={"queries_per_day": args.queries_per_day},
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
