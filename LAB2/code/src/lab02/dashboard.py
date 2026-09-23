"""Reproducible LAB02 dashboard for the 18 official trials."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .rq12_analysis import DEFAULT_DESIGN, DEFAULT_RAW_DIR, consolidate_trials
from .rq3_analysis import DEFAULT_METRICS_DIR, METRIC_FIELDS, METRIC_LABELS, consolidate_metrics


LAB2_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPORTS_DIR = LAB2_ROOT / "reports"
TREATMENT_LABELS = {"with_ai": "Com IA", "manual": "Manual"}
TREATMENT_ORDER = ["with_ai", "manual"]
METRIC_LABELS_DASHBOARD = {
    "elapsed_seconds": "Tempo (s)",
    "success_rate": "Taxa de sucesso (%)",
    "tests_failing": "Testes falhando",
    **METRIC_LABELS,
}


class DashboardError(RuntimeError):
    """Raised when dashboard inputs are incomplete or inconsistent."""


def consolidate_dashboard(
    design_path: Path = DEFAULT_DESIGN,
    raw_dir: Path = DEFAULT_RAW_DIR,
    metrics_dir: Path = DEFAULT_METRICS_DIR,
) -> pd.DataFrame:
    """Join RQ1/RQ2 and RQ3 rows using the official design as the key."""

    trial_rows = consolidate_trials(design_path, raw_dir)
    metric_rows = consolidate_metrics(design_path, metrics_dir, raw_dir)
    if len(trial_rows) != 18 or len(metric_rows) != 18:
        raise DashboardError("o dashboard exige exatamente os 18 trials oficiais")

    trial_frame = pd.DataFrame([row.to_csv_row() for row in trial_rows])
    metric_frame = pd.DataFrame([row.to_csv_row() for row in metric_rows])
    metric_frame = metric_frame.drop(columns=["participant", "kata_id", "treatment", "execution_order"])
    frame = trial_frame.merge(metric_frame, on="trial_id", how="inner", validate="one_to_one")
    if len(frame) != 18:
        raise DashboardError("a uniao das tabelas nao preservou os 18 trials oficiais")
    return frame.sort_values(["participant", "execution_order"]).reset_index(drop=True)


def _summary(frame: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    metrics = ["elapsed_seconds", "success_rate", "tests_failing", *METRIC_FIELDS]
    for treatment in TREATMENT_ORDER:
        treatment_frame = frame[frame["treatment"] == treatment]
        for metric in metrics:
            values = pd.to_numeric(treatment_frame[metric], errors="coerce").dropna()
            if values.empty:
                record = {"treatment": treatment, "metric": metric, "n": 0}
                record.update({name: None for name in ("q1", "median", "q3", "iqr", "min", "max")})
            else:
                q1, median, q3 = values.quantile([0.25, 0.5, 0.75])
                record = {
                    "treatment": treatment,
                    "metric": metric,
                    "n": int(values.size),
                    "q1": round(float(q1), 6),
                    "median": round(float(median), 6),
                    "q3": round(float(q3), 6),
                    "iqr": round(float(q3 - q1), 6),
                    "min": round(float(values.min()), 6),
                    "max": round(float(values.max()), 6),
                }
            records.append(record)
    return pd.DataFrame(records)


def _style_axis(axis: plt.Axes, title: str, ylabel: str) -> None:
    axis.set_title(title, loc="left", fontweight="bold")
    axis.set_xlabel("")
    axis.set_ylabel(ylabel)
    axis.grid(axis="y", alpha=0.25)
    axis.set_axisbelow(True)


def _plot_distribution(
    frame: pd.DataFrame,
    *,
    metric: str,
    title: str,
    ylabel: str,
    output: Path,
    censored: bool = False,
) -> None:
    plot_frame = frame[["participant", "trial_id", "treatment", metric, "censored"]].copy()
    plot_frame[metric] = pd.to_numeric(plot_frame[metric], errors="coerce")
    plot_frame = plot_frame.dropna(subset=[metric])
    plot_frame["treatment_label"] = plot_frame["treatment"].map(TREATMENT_LABELS)

    figure, axis = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    sns.boxplot(
        data=plot_frame,
        x="treatment_label",
        y=metric,
        order=[TREATMENT_LABELS[item] for item in TREATMENT_ORDER],
        width=0.42,
        showfliers=False,
        color="#d9e7e4",
        linecolor="#23413b",
        ax=axis,
    )
    sns.stripplot(
        data=plot_frame,
        x="treatment_label",
        y=metric,
        hue="participant",
        order=[TREATMENT_LABELS[item] for item in TREATMENT_ORDER],
        jitter=0.12,
        size=7,
        palette="Set2",
        edgecolor="white",
        linewidth=0.6,
        ax=axis,
    )
    if censored and plot_frame["censored"].any():
        censored_frame = plot_frame[plot_frame["censored"]]
        for treatment_index, treatment in enumerate(TREATMENT_ORDER):
            values = censored_frame.loc[censored_frame["treatment"] == treatment, metric]
            axis.scatter([treatment_index] * len(values), values, marker="X", s=70, color="#b7472a", zorder=5, label="Censurado")
    handles, labels = axis.get_legend_handles_labels()
    if handles:
        axis.legend(handles, labels, title="Participante", frameon=False, ncol=3)
    _style_axis(axis, title, ylabel)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _plot_rq2(frame: pd.DataFrame, output: Path) -> None:
    plot_frame = frame.melt(
        id_vars=["participant", "trial_id", "treatment", "censored"],
        value_vars=["success_rate", "tests_failing"],
        var_name="metric",
        value_name="value",
    )
    plot_frame["metric"] = plot_frame["metric"].map(METRIC_LABELS_DASHBOARD)
    plot_frame["treatment_label"] = plot_frame["treatment"].map(TREATMENT_LABELS)
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8), constrained_layout=True)
    for index, (axis, metric) in enumerate(zip(axes, ["Taxa de sucesso (%)", "Testes falhando"])):
        current = plot_frame[plot_frame["metric"] == metric]
        sns.boxplot(data=current, x="treatment_label", y="value", order=["Com IA", "Manual"], showfliers=False, color="#d9e7e4", ax=axis)
        sns.stripplot(data=current, x="treatment_label", y="value", hue="participant", order=["Com IA", "Manual"], jitter=0.12, size=7, palette="Set2", legend=index == 0, ax=axis)
        _style_axis(axis, metric, metric)
    axes[0].legend(title="Participante", frameon=False, ncol=3)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _plot_rq3(frame: pd.DataFrame, output: Path) -> None:
    plot_frame = frame.melt(
        id_vars=["participant", "trial_id", "treatment"],
        value_vars=list(METRIC_FIELDS),
        var_name="metric",
        value_name="value",
    ).dropna(subset=["value"])
    plot_frame["metric"] = plot_frame["metric"].map(METRIC_LABELS)
    plot_frame["treatment_label"] = plot_frame["treatment"].map(TREATMENT_LABELS)
    figure, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
    for index, (axis, metric) in enumerate(zip(axes.flat, [METRIC_LABELS[item] for item in METRIC_FIELDS])):
        current = plot_frame[plot_frame["metric"] == metric]
        sns.boxplot(data=current, x="treatment_label", y="value", order=["Com IA", "Manual"], showfliers=False, color="#d9e7e4", ax=axis)
        sns.stripplot(data=current, x="treatment_label", y="value", hue="participant", order=["Com IA", "Manual"], jitter=0.12, size=6, palette="Set2", legend=index == 0, ax=axis)
        _style_axis(axis, metric, "Valor")
    axes.flat[-1].axis("off")
    axes[0, 0].legend(title="Participante", frameon=False, ncol=3)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _summary_markdown(summary: pd.DataFrame) -> str:
    columns = ["treatment", "metric", "n", "q1", "median", "q3", "iqr", "min", "max"]
    labels = ["Tratamento", "Metrica", "n", "Q1", "Mediana", "Q3", "IQR", "Min", "Max"]
    lines = [
        "| " + " | ".join(labels) + " |",
        "| " + " | ".join("---" if index < 2 else "---:" for index in range(len(columns))) + " |",
    ]
    for row in summary[columns].itertuples(index=False, name=None):
        values = list(row)
        values[0] = TREATMENT_LABELS[values[0]]
        values[1] = METRIC_LABELS_DASHBOARD[values[1]]
        lines.append("| " + " | ".join("" if value is None else str(value) for value in values) + " |")
    return "\n".join(lines)


def _write_markdown(frame: pd.DataFrame, summary: pd.DataFrame, output: Path) -> None:
    censored_count = int(frame["censored"].sum())
    lines = [
        "# LAB02 - Dashboard",
        "",
        "Dashboard reproduzivel baseado exclusivamente nos 18 trials oficiais do contrabalanceamento.",
        "",
        f"- Trials: {len(frame)}",
        f"- Participantes: {frame['participant'].nunique()}",
        f"- Trials censurados: {censored_count}",
        "",
        "As figuras mostram cada trial como ponto, com mediana e IQR por tratamento. Pontos de trials censurados, quando existirem, sao marcados com X vermelho no grafico de tempo.",
        "",
        "## Artefatos",
        "",
        "- `figures/dashboard-rq1-time.png`: RQ1, tempo por tratamento.",
        "- `figures/dashboard-rq2-outcomes.png`: RQ2, taxa de sucesso e testes falhando.",
        "- `figures/dashboard-rq3-static-metrics.png`: RQ3, metricas estaticas.",
        "- `dashboard-trials.csv`: tabela unificada por trial.",
        "- `dashboard-summary.csv`: mediana, quartis e IQR por tratamento e metrica.",
        "",
        "## Resumo",
        "",
        _summary_markdown(summary),
        "",
        "## Reproducao",
        "",
        "A partir de `LAB2/code`, execute `python -m lab02.dashboard` (ou `lab02-dashboard` apos instalar o pacote).",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera o dashboard reprodutivel do LAB02.")
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--metrics-dir", type=Path, default=DEFAULT_METRICS_DIR)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        frame = consolidate_dashboard(args.design, args.raw_dir, args.metrics_dir)
        summary = _summary(frame)
        figures_dir = args.reports_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(args.reports_dir / "dashboard-trials.csv", index=False)
        summary.to_csv(args.reports_dir / "dashboard-summary.csv", index=False)
        _plot_distribution(frame, metric="elapsed_seconds", title="RQ1 | Tempo por tratamento", ylabel="Tempo decorrido (s)", output=figures_dir / "dashboard-rq1-time.png", censored=True)
        _plot_rq2(frame, figures_dir / "dashboard-rq2-outcomes.png")
        _plot_rq3(frame, figures_dir / "dashboard-rq3-static-metrics.png")
        _write_markdown(frame, summary, args.reports_dir / "dashboard-summary.md")
    except (DashboardError, OSError, ValueError, KeyError) as error:
        print(f"ERRO: {error}")
        return 1

    print(f"Dashboard: {len(frame)} trials oficiais")
    print(f"Relatorios: {args.reports_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())