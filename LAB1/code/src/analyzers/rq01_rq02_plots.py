"""Gera visualizacoes e interpretacoes das RQ01 e RQ02."""

from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean, median

import matplotlib.pyplot as plt
import seaborn as sns

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from analyzers.rq01_rq02_consistency import describe, find_outliers
from validators.rq01_rq02 import validate_dataset
from visualization.figures import figure_path
from visualization.loader import load_top_repositories
from visualization.style import PALETTE, apply_common_style, save_figure


REPORT_PATH = Path(__file__).resolve().parents[3] / "reports" / "rq01-rq02.md"


def format_number(value: float) -> str:
    """Formata inteiros e decimais para o relatorio em portugues."""
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".replace(".", ",")


def plot_rq01_age(ages: list[int], output_path: Path) -> dict:
    """Gera histograma da idade dos repositorios com mediana e media."""
    age_median = median(ages)
    age_mean = mean(ages)

    figure, ax = plt.subplots(figsize=(10, 6))
    ax.hist(ages, bins=30, color=PALETTE["primary"], edgecolor="white")
    ax.axvline(
        age_median,
        color=PALETTE["accent"],
        linestyle="--",
        linewidth=2,
        label=f"Mediana = {format_number(age_median)} dias",
    )
    ax.axvline(
        age_mean,
        color=PALETTE["secondary"],
        linestyle=":",
        linewidth=2,
        label=f"Media = {format_number(age_mean)} dias",
    )
    ax.set_title("RQ01 - Distribuicao da idade dos repositorios")
    ax.set_xlabel("Idade do repositorio (dias)")
    ax.set_ylabel("Quantidade de repositorios")
    ax.legend(loc="upper left")
    save_figure(figure, output_path)

    return {
        "count": len(ages),
        "median": age_median,
        "mean": age_mean,
        "min": min(ages),
        "max": max(ages),
    }


def plot_rq02_merged_prs(
    repositories: list[dict], output_path: Path
) -> dict:
    """Gera boxplot de PRs aceitas preservando outliers em escala symlog."""
    merged_prs = [repository["merged_pull_requests"] for repository in repositories]
    summary = describe(merged_prs)
    outliers = find_outliers(repositories, "merged_pull_requests", summary)

    figure, ax = plt.subplots(figsize=(11, 5))
    sns.boxplot(
        x=merged_prs,
        ax=ax,
        color=PALETTE["primary"],
        showfliers=True,
        flierprops={
            "marker": "o",
            "markerfacecolor": PALETTE["accent"],
            "markeredgecolor": PALETTE["accent"],
            "markersize": 3,
            "alpha": 0.55,
        },
    )
    ax.axvline(
        summary["median"],
        color=PALETTE["accent"],
        linestyle="--",
        linewidth=2,
        label=f"Mediana = {format_number(summary['median'])} PRs",
    )
    ax.set_xscale("symlog", linthresh=100)
    ax.set_xlim(0, max(merged_prs) * 1.05)
    ax.set_title(
        "RQ02 - Distribuicao de Pull Requests aceitas\n"
        f"Escala symlog; {len(outliers)} outliers pelo metodo IQR"
    )
    ax.set_xlabel("Pull Requests aceitas (escala symlog)")
    ax.set_ylabel("")
    ax.legend(loc="upper left")
    save_figure(figure, output_path)

    return {
        **summary,
        "outlier_count": len(outliers),
        "zero_count": sum(value == 0 for value in merged_prs),
        "at_least_1000": sum(value >= 1000 for value in merged_prs),
    }


def build_visualization_section(rq01: dict, rq02: dict) -> str:
    """Monta a interpretacao objetiva das duas figuras."""
    return f"""## Visualizacoes (Lab01S03)

As figuras foram geradas a partir dos {rq01['count']} registros validados do CSV
consolidado:

- `reports/figures/rq01_idade.png`
- `reports/figures/rq02_pull_requests.png`

### Interpretacao da figura RQ01

O histograma mostra idade mediana de **{format_number(rq01['median'])} dias**
({rq01['median'] / 365:.2f} anos) e media de
**{format_number(rq01['mean'])} dias** ({rq01['mean'] / 365:.2f} anos). Os valores variam de
{format_number(rq01['min'])} a {format_number(rq01['max'])} dias. A proximidade
entre media e mediana e a concentracao visual em varios anos sustentam que os
repositorios populares analisados tendem a ser maduros.

### Interpretacao da figura RQ02

O boxplot usa escala `symlog` para manter visiveis os valores zero e os projetos
com volumes muito altos. A mediana e
**{format_number(rq02['median'])} PRs aceitas**, enquanto a media e
**{format_number(rq02['mean'])}**, evidenciando uma
distribuicao assimetrica. Pelo mesmo criterio IQR da Issue #21, foram preservados
e exibidos **{rq02['outlier_count']} outliers** acima de
**{format_number(rq02['upper_bound'])} PRs**. Ha {rq02['zero_count']} repositorios sem
PRs aceitas e {rq02['at_least_1000']} com pelo menos 1.000, confirmando grande
variacao na contribuicao externa.
"""


def update_report(rq01: dict, rq02: dict) -> None:
    """Acrescenta ou atualiza a secao de visualizacoes no relatorio existente."""
    current = REPORT_PATH.read_text(encoding="utf-8")
    marker = "## Visualizacoes (Lab01S03)"
    section = build_visualization_section(rq01, rq02)
    before = current.split(marker)[0].rstrip() if marker in current else current.rstrip()
    REPORT_PATH.write_text(before + "\n\n" + section, encoding="utf-8")


def main() -> None:
    apply_common_style()
    repositories = load_top_repositories()
    validate_dataset(repositories, expected_count=1000)

    rq01_path = figure_path("rq01", "idade")
    rq02_path = figure_path("rq02", "pull_requests")
    rq01 = plot_rq01_age(
        [repository["repository_age_days"] for repository in repositories],
        rq01_path,
    )
    rq02 = plot_rq02_merged_prs(repositories, rq02_path)
    update_report(rq01, rq02)

    print(f"RQ01: {rq01_path}")
    print(f"RQ02: {rq02_path}")
    print(f"Relatorio atualizado: {REPORT_PATH}")
    print(
        f"Medianas: idade={format_number(rq01['median'])} dias; "
        f"PRs={format_number(rq02['median'])}; outliers IQR={rq02['outlier_count']}"
    )


if __name__ == "__main__":
    main()
