"""Estilo comum e backend sem interface grafica para Matplotlib/Seaborn."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns

from validators.figures import validate_figure_definition


FIGURE_DPI = 150
FIGURE_SIZE = (10, 6)

PALETTE = {
    "primary": "#1f4e79",
    "secondary": "#5b9bd5",
    "accent": "#c45911",
    "neutral": "#7f7f7f",
    "grid": "#d9d9d9",
}


def apply_common_style() -> None:
    """Aplica tipografia, cores e layout padrao reutilizavel pelas RQs."""
    sns.set_theme(
        style="whitegrid",
        context="notebook",
        font="DejaVu Sans",
        rc={
            "figure.figsize": FIGURE_SIZE,
            "figure.dpi": FIGURE_DPI,
            "savefig.dpi": FIGURE_DPI,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "axes.titleweight": "bold",
            "axes.edgecolor": "#333333",
            "axes.labelcolor": "#222222",
            "text.color": "#222222",
            "grid.color": PALETTE["grid"],
            "axes.facecolor": "white",
            "figure.facecolor": "white",
        },
    )


def save_figure(fig: plt.Figure, output_path: Path) -> Path:
    """Salva a figura em PNG com resolucao padrao."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rq = output_path.name[:4].upper()
    if rq in {f"RQ{index:02d}" for index in range(1, 8)}:
        validate_figure_definition(rq, fig)
    fig.tight_layout()
    fig.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)
    return output_path
