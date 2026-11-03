"""Figuras G1 e G2 do LAB04S01."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from .hypothesis_tests import welch_t_test

COLOR_BOT = "#1f77b4"
COLOR_HUMAN = "#ff7f0e"
COLOR_WELCH = "#2ca02c"
COLOR_MW = "#d62728"


def plot_g1(
    real_data: pd.DataFrame,
    simulated_data: pd.DataFrame,
    output_path: Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    panels = [
        (axes[0], real_data, "G1a — Dados reais"),
        (axes[1], simulated_data, "G1b — Dados simulados"),
    ]
    for axis, frame, title in panels:
        for group, color in (("bot", COLOR_BOT), ("human", COLOR_HUMAN)):
            values = frame.loc[frame["group"] == group, "duration_hours"].to_numpy(dtype=float)
            axis.hist(
                values,
                bins=12,
                alpha=0.55,
                color=color,
                label=group,
                edgecolor="white",
            )
        axis.set_title(title)
        axis.set_xlabel("Tempo ate o merge (horas)")
        axis.set_ylabel("Frequencia")
        axis.legend(title="Grupo")
    fig.suptitle("G1 — Histogramas dos tempos de merge por grupo")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_g2(
    null_statistics: np.ndarray,
    example_statistic: float,
    example_p_value: float,
    alpha: float,
    output_path: Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    values = np.asarray(null_statistics, dtype=float)
    critical_low = float(np.quantile(values, alpha / 2))
    critical_high = float(np.quantile(values, 1 - alpha / 2))

    fig, axis = plt.subplots(figsize=(9, 4.8))
    axis.hist(values, bins=40, density=True, color=COLOR_WELCH, alpha=0.55, edgecolor="white", label="Welch sob H0")
    xs = np.linspace(values.min(), values.max(), 300)
    kde = stats.gaussian_kde(values)
    axis.plot(xs, kde(xs), color="black", linewidth=1.5, label="Densidade estimada")

    ymin, ymax = axis.get_ylim()
    axis.axvspan(values.min(), critical_low, color=COLOR_MW, alpha=0.15, label="Regiao de rejeicao")
    axis.axvspan(critical_high, values.max(), color=COLOR_MW, alpha=0.15)
    axis.axvline(example_statistic, color="black", linestyle="--", linewidth=1.8, label=f"Exemplo t={example_statistic:.3f}")
    axis.set_ylim(ymin, ymax)
    axis.set_title("G2 — Estatistica t de Welch sob H0, rejeicao e exemplo")
    axis.set_xlabel("Estatistica t de Welch")
    axis.set_ylabel("Densidade")
    axis.legend(loc="upper right")
    axis.text(
        0.02,
        0.95,
        f"alpha={alpha:.2f}\np-valor exemplo={example_p_value:.4f}",
        transform=axis.transAxes,
        va="top",
        ha="left",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def null_welch_statistics(
    config: dict,
    *,
    replications: int | None = None,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, float, float]:
    from .simulate import simulate_dataset

    reps = int(replications if replications is not None else config["replications"])
    generator = rng or np.random.default_rng(int(config["random_seed"]) + 1)
    stats_values = np.empty(reps, dtype=float)
    for index in range(reps):
        frame = simulate_dataset(config, under_null=True, effect_hours=0.0, rng=generator)
        bot = frame.loc[frame["group"] == "bot", "duration_hours"].to_numpy()
        human = frame.loc[frame["group"] == "human", "duration_hours"].to_numpy()
        stats_values[index] = welch_t_test(bot, human, alternative=config["alternative"], alpha=config["alpha"]).statistic

    example = simulate_dataset(config, under_null=True, effect_hours=0.0, rng=generator)
    bot = example.loc[example["group"] == "bot", "duration_hours"].to_numpy()
    human = example.loc[example["group"] == "human", "duration_hours"].to_numpy()
    example_result = welch_t_test(bot, human, alternative=config["alternative"], alpha=config["alpha"])
    return stats_values, example_result.statistic, example_result.p_value
