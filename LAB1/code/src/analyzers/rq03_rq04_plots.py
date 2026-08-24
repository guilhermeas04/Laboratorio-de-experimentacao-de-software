"""Visualizacoes das RQ03 e RQ04 a partir do CSV de 1000 repositorios."""

from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean, median

import matplotlib.pyplot as plt
import seaborn as sns

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validators.rq03_rq04 import validate_dataset
from visualization.figures import figure_path
from visualization.loader import load_top_repositories
from visualization.style import PALETTE, apply_common_style, save_figure


DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[3] / "reports" / "rq03-rq04.md"


def format_number(value: float) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".replace(".", ",")


def plot_rq03_releases(releases: list[int], output_path: Path) -> dict:
    """Histograma do total de releases com mediana."""
    release_median = median(releases)
    release_mean = mean(releases)
    zeros = sum(1 for value in releases if value == 0)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(releases, bins=40, color=PALETTE["primary"], edgecolor="white")
    ax.axvline(
        release_median,
        color=PALETTE["accent"],
        linestyle="--",
        linewidth=2,
        label=f"Mediana = {format_number(release_median)} releases",
    )
    ax.axvline(
        release_mean,
        color=PALETTE["secondary"],
        linestyle=":",
        linewidth=2,
        label=f"Media = {format_number(release_mean)} releases",
    )
    ax.set_title("RQ03 - Distribuicao do total de releases")
    ax.set_xlabel("Total de releases")
    ax.set_ylabel("Quantidade de repositorios")
    ax.legend(loc="upper right")

    save_figure(fig, output_path)
    return {
        "median": release_median,
        "mean": release_mean,
        "zeros": zeros,
        "min": min(releases),
        "max": max(releases),
        "count": len(releases),
    }


def plot_rq04_update_comparison(
    days_update: list[int],
    days_push: list[int],
    output_path: Path,
) -> dict:
    """Compara dias desde updatedAt e pushedAt (boxplot)."""
    update_median = median(days_update)
    push_median = median(days_push)
    update_mean = mean(days_update)
    push_mean = mean(days_push)
    updated_zero = sum(1 for value in days_update if value == 0)
    pushed_zero = sum(1 for value in days_push if value == 0)

    fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=False)

    sns.boxplot(
        y=days_update,
        ax=axes[0],
        color=PALETTE["secondary"],
        showfliers=True,
    )
    axes[0].axhline(
        update_median,
        color=PALETTE["accent"],
        linestyle="--",
        linewidth=2,
        label=f"Mediana = {format_number(update_median)} dias",
    )
    axes[0].set_title("Dias desde updatedAt")
    axes[0].set_ylabel("Dias")
    axes[0].set_xlabel("")
    axes[0].legend(loc="upper right")

    sns.boxplot(
        y=days_push,
        ax=axes[1],
        color=PALETTE["primary"],
        showfliers=True,
    )
    axes[1].axhline(
        push_median,
        color=PALETTE["accent"],
        linestyle="--",
        linewidth=2,
        label=f"Mediana = {format_number(push_median)} dias",
    )
    axes[1].set_title("Dias desde pushedAt")
    axes[1].set_ylabel("Dias")
    axes[1].set_xlabel("")
    axes[1].legend(loc="upper right")

    fig.suptitle(
        "RQ04 - Comparacao updatedAt vs pushedAt\n"
        "Limitacao: updatedAt muda com qualquer atividade e quase nao discrimina",
        fontsize=13,
        fontweight="bold",
    )

    save_figure(fig, output_path)
    return {
        "update_median": update_median,
        "update_mean": update_mean,
        "push_median": push_median,
        "push_mean": push_mean,
        "updated_zero": updated_zero,
        "pushed_zero": pushed_zero,
        "count": len(days_update),
    }


def build_visualization_section(rq03: dict, rq04: dict) -> str:
    """Interpreta os valores exibidos nas figuras."""
    return f"""## Visualizacoes (Lab01S03)

Figuras geradas a partir dos {rq03["count"]} registros do CSV consolidado:

- `reports/figures/rq03_releases.png`
- `reports/figures/rq04_atualizacao.png`

### Interpretacao da figura RQ03

O histograma do total de releases mostra concentracao a esquerda: mediana de
{format_number(rq03["median"])} releases e media de {format_number(rq03["mean"])}.
Ha {rq03["zeros"]} repositorios com zero releases (minimo {format_number(rq03["min"])},
maximo {format_number(rq03["max"])}). A mediana, marcada no grafico, fica bem abaixo
da media, confirmando cauda longa e uso heterogeneo de releases.

### Interpretacao da figura RQ04

A comparacao visual deixa clara a limitacao de `updatedAt`: mediana de
{format_number(rq04["update_median"])} dias e {rq04["updated_zero"]} repositorios
atualizados no dia da coleta. Em contraste, `pushedAt` tem mediana de
{format_number(rq04["push_median"])} dias, media de {format_number(rq04["push_mean"])}
e {rq04["pushed_zero"]} repositorios com push no dia da coleta. A dispersao de
`pushedAt` e bem maior, por isso essa metrica responde melhor a RQ04.

Outliers e a limitacao de `updatedAt` seguem o registrado em
`reports/validacao-rq03-rq04.md` (Issue #22).
"""


def update_report(rq03: dict, rq04: dict) -> None:
    """Acrescenta a interpretacao das figuras ao relatorio existente."""
    report_path = DEFAULT_REPORT_PATH
    current = report_path.read_text(encoding="utf-8")
    marker = "## Visualizacoes (Lab01S03)"
    section = build_visualization_section(rq03, rq04)

    if marker in current:
        before = current.split(marker)[0].rstrip()
        report_path.write_text(before + "\n\n" + section, encoding="utf-8")
    else:
        report_path.write_text(current.rstrip() + "\n\n" + section, encoding="utf-8")


def main() -> None:
    apply_common_style()
    repositories = load_top_repositories()
    summary = validate_dataset(repositories, expected_count=1000)

    if summary["missing"] or summary["invalid"]:
        raise ValueError(
            "Validacao RQ03/RQ04 falhou: "
            f"ausentes={len(summary['missing'])}, "
            f"invalidos={len(summary['invalid'])}"
        )

    rq03_path = figure_path("rq03", "releases")
    rq04_path = figure_path("rq04", "atualizacao")

    rq03 = plot_rq03_releases(summary["releases"], rq03_path)
    rq04 = plot_rq04_update_comparison(
        summary["days_update"],
        summary["days_push"],
        rq04_path,
    )
    update_report(rq03, rq04)

    print(f"RQ03: {rq03_path}")
    print(f"RQ04: {rq04_path}")
    print(f"Relatorio atualizado: {DEFAULT_REPORT_PATH}")
    print(
        "Limitacao updatedAt: mediana="
        f"{format_number(rq04['update_median'])} dias; "
        f"zero dias={rq04['updated_zero']}"
    )


if __name__ == "__main__":
    main()
