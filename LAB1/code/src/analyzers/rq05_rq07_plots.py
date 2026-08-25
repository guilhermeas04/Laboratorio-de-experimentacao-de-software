"""Gera as visualizacoes e interpretacoes das RQ05, RQ06 e RQ07."""

from __future__ import annotations

import sys
from pathlib import Path
from statistics import median

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import seaborn as sns

SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validators.rq05_rq06 import POPULAR_LANGUAGES, validate_dataset
from validators.rq07 import group_by_language, validate_dataset as validate_rq07
from visualization.figures import figure_path
from visualization.loader import load_top_repositories
from visualization.style import PALETTE, apply_common_style, save_figure


REPORT_PATH = Path(__file__).resolve().parents[3] / "reports" / "rq05-rq06-rq07-visualizacoes.md"
SMALL_GROUP_THRESHOLD = 5


def _language_label(language: str) -> str:
    return language or "Sem linguagem"


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".replace(".", ",")


def plot_rq05_languages(language_counts: dict[str, int], output_path: Path) -> dict:
    """Gera ranking horizontal das linguagens, destacando o top 10 do Octoverse."""
    ordered = sorted(language_counts.items(), key=lambda item: (-item[1], item[0]))
    labels = [_language_label(language) for language, _ in ordered]
    counts = [count for _, count in ordered]
    colors = [
        PALETTE["primary"] if language in POPULAR_LANGUAGES else PALETTE["secondary"]
        for language, _ in ordered
    ]

    height = max(6, 0.28 * len(ordered))
    fig, ax = plt.subplots(figsize=(11, height))
    bars = ax.barh(labels[::-1], counts[::-1], color=colors[::-1])
    for bar, count in zip(bars, counts[::-1]):
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height() / 2, str(count), va="center")
    ax.set_title("RQ05 - Ranking das linguagens primarias")
    ax.set_xlabel("Quantidade de repositorios")
    ax.set_ylabel("Linguagem")
    ax.legend(
        handles=[
            Patch(color=PALETTE["primary"], label="Top 10 do Octoverse 2024"),
            Patch(color=PALETTE["secondary"], label="Fora do top 10"),
        ],
        loc="lower right",
    )
    save_figure(fig, output_path)
    return {"ordered": ordered, "top_language": ordered[0], "top10_count": sum(language_counts.get(language, 0) for language in POPULAR_LANGUAGES)}


def plot_rq06_closed_issues(repositories: list[dict], output_path: Path) -> dict:
    """Gera a distribuicao percentual das issues fechadas."""
    ratios = [repository["closed_issues_ratio"] * 100 for repository in repositories if repository["closed_issues_ratio"] is not None]
    figure, ax = plt.subplots(figsize=(10, 6))
    ax.hist(ratios, bins=20, range=(0, 100), color=PALETTE["primary"], edgecolor="white")
    ratio_median = median(ratios)
    ax.axvline(ratio_median, color=PALETTE["accent"], linestyle="--", linewidth=2, label=f"Mediana = {ratio_median:.2f}%")
    ax.set_title("RQ06 - Distribuicao do percentual de issues fechadas")
    ax.set_xlabel("Issues fechadas (%)")
    ax.set_ylabel("Quantidade de repositorios")
    ax.set_xlim(0, 100)
    ax.legend(loc="upper left")
    save_figure(figure, output_path)
    return {
        "count": len(ratios),
        "without_issues": len(repositories) - len(ratios),
        "median": ratio_median,
        "at_least_75": sum(ratio >= 75 for ratio in ratios),
        "at_least_90": sum(ratio >= 90 for ratio in ratios),
    }


def plot_rq07_language_metrics(repositories: list[dict], output_path: Path) -> dict:
    """Gera dispersao de medianas de PRs e releases com tamanho do grupo."""
    groups = group_by_language(repositories)
    push_groups: dict[str, list[int]] = {}
    for repository in repositories:
        language = (repository["primary_language"] or "").strip()
        push_groups.setdefault(language, []).append(repository["days_since_last_push"])
    rows = []
    for language, items in groups.items():
        rows.append({
            "language": _language_label(language),
            "is_top10": language in POPULAR_LANGUAGES,
            "count": len(items),
            "prs": median(item["merged_pull_requests"] for item in items),
            "releases": median(item["releases_count"] for item in items),
            "push_days": median(push_groups[language]),
        })
    rows.sort(key=lambda row: (-row["count"], row["language"]))

    figure, ax = plt.subplots(figsize=(12, 8))
    for row in rows:
        color = PALETTE["primary"] if row["is_top10"] else PALETTE["secondary"]
        edge = PALETTE["accent"] if row["count"] < SMALL_GROUP_THRESHOLD else "white"
        ax.scatter(row["prs"], row["releases"], s=35 + row["count"] * 18, color=color, edgecolor=edge, linewidth=1.5, alpha=0.85)
        ax.annotate(row["language"], (row["prs"], row["releases"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_xscale("symlog", linthresh=1)
    ax.set_yscale("symlog", linthresh=1)
    ax.set_title("RQ07 - Medianas de PRs e releases por linguagem")
    ax.set_xlabel("Mediana de PRs aceitas (escala simetrica log)")
    ax.set_ylabel("Mediana de releases (escala simetrica log)")
    ax.legend(handles=[
        Line2D([0], [0], marker="o", color="w", markerfacecolor=PALETTE["primary"], label="Top 10 do Octoverse", markersize=9),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=PALETTE["secondary"], label="Fora do top 10", markersize=9),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="white", markeredgecolor=PALETTE["accent"], label="Grupo < 5 projetos", markersize=9),
    ], loc="upper left")
    save_figure(figure, output_path)
    return {"rows": rows, "small_groups": [row for row in rows if row["count"] < SMALL_GROUP_THRESHOLD]}


def build_report(rq05: dict, rq06: dict, rq07: dict) -> str:
    """Registra interpretacoes objetivas dos valores exibidos."""
    top_language, top_count = rq05["top_language"]
    top_language_label = _language_label(top_language)
    top_group = rq07["rows"][0]
    push_order = sorted(rq07["rows"], key=lambda row: row["push_days"])
    return f"""# Visualizacoes das RQ05, RQ06 e RQ07

Base: **{rq06['count'] + rq06['without_issues']} repositorios**.

## Arquivos gerados

- `reports/figures/rq05_linguagens.png`
- `reports/figures/rq06_issues.png`
- `reports/figures/rq07_linguagem_metricas.png`

## Interpretacao objetiva

- **RQ05:** `{top_language_label}` e a linguagem mais frequente, com {top_count} repositorios. O top 10 do Octoverse concentra {rq05['top10_count']} de {rq06['count'] + rq06['without_issues']} repositorios. No grafico, azul identifica linguagens do top 10 e azul-claro as demais.
- **RQ06:** a mediana do percentual de issues fechadas e {rq06['median']:.2f}% entre {rq06['count']} repositorios com issues. {rq06['at_least_75']} atingem pelo menos 75% e {rq06['at_least_90']} atingem pelo menos 90%; {rq06['without_issues']} nao entram na distribuicao por nao possuirem issues.
- **RQ07:** o maior grupo e `{top_group['language']}`, com {top_group['count']} projetos. Cada ponto mostra as medianas de PRs e releases; seu tamanho representa a quantidade de projetos. Ha {len(rq07['small_groups'])} grupos com menos de cinco projetos, marcados com borda laranja. A mediana de `pushedAt` e usada como complemento de atualizacao: o grupo com menor mediana e `{push_order[0]['language']}` ({_format_number(push_order[0]['push_days'])} dias) e o maior e `{push_order[-1]['language']}` ({_format_number(push_order[-1]['push_days'])} dias).
"""


def main() -> None:
    apply_common_style()
    repositories = load_top_repositories()
    rq05 = validate_dataset(repositories, expected_count=1000)
    validate_rq07(repositories, expected_count=1000)
    rq05_result = plot_rq05_languages(rq05["languages"], figure_path("rq05", "linguagens"))
    rq06_result = plot_rq06_closed_issues(repositories, figure_path("rq06", "issues"))
    rq07_result = plot_rq07_language_metrics(repositories, figure_path("rq07", "linguagem_metricas"))
    REPORT_PATH.write_text(build_report(rq05_result, rq06_result, rq07_result), encoding="utf-8")
    print(f"Figuras geradas em: {figure_path('rq05', 'linguagens').parent}")
    print(f"Relatorio gerado: {REPORT_PATH}")


if __name__ == "__main__":
    main()