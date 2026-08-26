"""Gera um grafico de teste do pipeline sem intervencao manual."""

from __future__ import annotations

import sys
from pathlib import Path
from statistics import median

import matplotlib.pyplot as plt

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from visualization.figures import FIGURES_DIR
from visualization.loader import load_top_repositories
from visualization.style import PALETTE, apply_common_style, save_figure


def main() -> None:
    apply_common_style()
    repositories = load_top_repositories()
    ages = [repository["repository_age_days"] for repository in repositories]
    age_median = median(ages)

    fig, ax = plt.subplots()
    ax.hist(ages, bins=30, color=PALETTE["primary"], edgecolor="white")
    ax.axvline(
        age_median,
        color=PALETTE["accent"],
        linestyle="--",
        linewidth=2,
        label=f"Mediana = {age_median:.0f} dias",
    )
    ax.set_title("Smoke test do pipeline - idade dos repositorios")
    ax.set_xlabel("Idade (dias)")
    ax.set_ylabel("Quantidade de repositorios")
    ax.legend(loc="upper right")

    output_path = FIGURES_DIR / "smoke_test.png"
    save_figure(fig, output_path)

    print(f"Registros carregados e validados: {len(repositories)}")
    print(f"Figura de teste: {output_path}")


if __name__ == "__main__":
    main()
