"""Figuras G3 e G4 do LAB04S02."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .plots import COLOR_MW, COLOR_WELCH

TEST_COLORS = {"welch_t": COLOR_WELCH, "mann_whitney": COLOR_MW}
TEST_LABELS = {"welch_t": "t de Welch", "mann_whitney": "Mann-Whitney"}
SITUATION_LABELS = {
    "ideal": "Ideal (n=30)",
    "small_sample": "Amostra pequena (n=8)",
    "extreme_outlier": "Outliers (5% x20)",
}
SITUATION_STYLES = {"ideal": "-", "small_sample": "--", "extreme_outlier": ":"}
SITUATION_MARKERS = {"ideal": "o", "small_sample": "s", "extreme_outlier": "^"}


def _situations(frame: pd.DataFrame) -> list[str]:
    ordered = [name for name in SITUATION_LABELS if name in set(frame["situation"])]
    extras = sorted(set(frame["situation"]) - set(ordered))
    return ordered + extras


def plot_g3(type_i: pd.DataFrame, output_path: Path, *, alpha: float = 0.05) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    situations = _situations(type_i)
    tests = [name for name in TEST_COLORS if name in set(type_i["test_name"])]
    positions = np.arange(len(situations))
    width = 0.8 / len(tests)

    fig, axis = plt.subplots(figsize=(9, 5))
    for index, test in enumerate(tests):
        rates = [
            float(
                type_i.loc[(type_i["situation"] == situation) & (type_i["test_name"] == test), "rejection_rate"].iloc[0]
            )
            * 100
            for situation in situations
        ]
        bars = axis.bar(
            positions + (index - (len(tests) - 1) / 2) * width,
            rates,
            width=width,
            color=TEST_COLORS[test],
            label=TEST_LABELS[test],
        )
        axis.bar_label(bars, labels=[f"{rate:.2f}%".replace(".", ",") for rate in rates], padding=2, fontsize=9)

    axis.axhline(alpha * 100, color="black", linestyle="--", linewidth=1.5, label=f"Referência alpha = {alpha:.0%}")
    axis.set_xticks(positions, [SITUATION_LABELS.get(name, name) for name in situations])
    axis.set_title("G3 — Erro tipo I de Welch e Mann-Whitney por situação simulada")
    axis.set_xlabel("Situação simulada (H0 verdadeira)")
    axis.set_ylabel("Erro tipo I (% de rejeições de H0)")
    axis.set_ylim(0, max(alpha * 100 * 2, float(type_i["rejection_rate"].max()) * 100 * 1.25))
    axis.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_g4(power: pd.DataFrame, output_path: Path, *, alpha: float = 0.05) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axis = plt.subplots(figsize=(9.5, 5.5))
    for situation in _situations(power):
        for test in TEST_COLORS:
            subset = power[(power["situation"] == situation) & (power["test_name"] == test)].sort_values("effect_hours")
            if subset.empty:
                continue
            axis.plot(
                subset["effect_hours"],
                subset["power"] * 100,
                color=TEST_COLORS[test],
                linestyle=SITUATION_STYLES.get(situation, "-."),
                marker=SITUATION_MARKERS.get(situation, "x"),
                linewidth=1.8,
                label=f"{TEST_LABELS[test]} — {SITUATION_LABELS.get(situation, situation)}",
            )

    axis.axhline(alpha * 100, color="gray", linestyle="--", linewidth=1, label=f"alpha = {alpha:.0%}")
    axis.set_title("G4 — Curvas de poder de Welch e Mann-Whitney")
    axis.set_xlabel("Tamanho do efeito (deslocamento no tempo de merge, horas)")
    axis.set_ylabel("Poder (% de rejeições de H0)")
    axis.set_ylim(0, 100)
    axis.legend(loc="upper left", fontsize=8)
    axis.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
