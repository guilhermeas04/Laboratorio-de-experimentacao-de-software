"""Análise descritiva reproduzível da coleta completa LAB05S02."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "data" / "processed" / "lab05s02-20261121-01_validated.csv"
DEFAULT_TABLES = ROOT / "reports" / "tables"
DEFAULT_FIGURES = ROOT / "reports" / "figures"
DEFAULT_DOCS = ROOT / "docs"
ROUND_KEY = ["block", "scenario", "software_version"]

IDENTITY_COLUMNS = (
    "campaign_id",
    "block",
    "position",
    "software_version",
    "scenario",
    "execution_id",
    "round_id",
    "source",
)

CORE_METRICS = (
    "query_latency_ms",
    "throughput_queries_per_second",
    "cpu_percent",
    "memory_mb",
)

AUX_METRICS = (
    "client_latency_ms",
    "resource_window_seconds",
)

METRIC_CATALOG: dict[str, dict[str, str]] = {
    "query_latency_ms": {
        "unit": "ms",
        "scale": "ratio",
        "aggregation": (
            "Mediana de cinco Execution Time do EXPLAIN ANALYZE por rodada; "
            "na análise descritiva, cada rodada validada é uma observação."
        ),
    },
    "throughput_queries_per_second": {
        "unit": "consultas/s",
        "scale": "ratio",
        "aggregation": (
            "TPS do pgbench sem tempo de conexão inicial; "
            "cada rodada validada contribui com um valor."
        ),
    },
    "cpu_percent": {
        "unit": "%",
        "scale": "ratio",
        "aggregation": (
            "Média do uso de CPU no cgroup na janela amostrada; "
            "sem imputação de ausentes."
        ),
    },
    "memory_mb": {
        "unit": "MB",
        "scale": "ratio",
        "aggregation": (
            "Média da memória do cgroup na janela amostrada; "
            "sem imputação de ausentes."
        ),
    },
    "client_latency_ms": {
        "unit": "ms",
        "scale": "ratio",
        "aggregation": "Latência média reportada pelo pgbench por rodada.",
    },
    "resource_window_seconds": {
        "unit": "s",
        "scale": "ratio",
        "aggregation": "Duração da janela usada para amostrar CPU/memória.",
    },
}


class CompleteAnalysisError(ValueError):
    """Indica falha na análise descritiva da coleta completa."""


def load_validated_dataset(path: str | Path) -> pd.DataFrame:
    """Carrega o CSV validado preservando versões como texto e ausentes como NaN."""

    dataset_path = Path(path)
    if not dataset_path.is_file():
        raise CompleteAnalysisError(f"dataset validado não encontrado: {dataset_path}")

    frame = pd.read_csv(
        dataset_path,
        dtype={
            "campaign_id": "string",
            "software_version": "string",
            "scenario": "string",
            "execution_id": "string",
            "round_id": "string",
            "source": "string",
        },
    )
    required = {"campaign_id", "block", "software_version", "scenario", "source"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise CompleteAnalysisError(f"colunas obrigatórias ausentes: {', '.join(missing)}")

    for column in list(CORE_METRICS) + list(AUX_METRICS):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    blocks = pd.to_numeric(frame["block"], errors="coerce")
    if blocks.isna().any() or not ((blocks > 0) & (blocks % 1 == 0)).all():
        raise CompleteAnalysisError("block deve conter inteiros positivos")
    frame["block"] = blocks.astype("Int64")
    if "position" in frame.columns:
        frame["position"] = pd.to_numeric(frame["position"], errors="coerce").astype("Int64")
    if frame.empty:
        raise CompleteAnalysisError("dataset validado sem rodadas")
    for name in ("campaign_id", "software_version", "scenario", "source"):
        if frame[name].isna().any() or frame[name].str.strip().eq("").any():
            raise CompleteAnalysisError(f"{name} ausente no dataset validado")
    if frame["campaign_id"].nunique() != 1:
        raise CompleteAnalysisError("o dataset deve conter uma única campanha")
    if frame.duplicated(ROUND_KEY).any():
        raise CompleteAnalysisError("rodadas duplicadas por bloco, cenário e versão")
    return frame


def available_metrics(frame: pd.DataFrame, candidates: Iterable[str] | None = None) -> list[str]:
    names = list(candidates) if candidates is not None else list(CORE_METRICS) + list(AUX_METRICS)
    return [name for name in names if name in frame.columns]


def _observed(series: pd.Series) -> np.ndarray:
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    return values[np.isfinite(values)]


def descriptive_by_version_scenario(frame: pd.DataFrame, metrics: Iterable[str]) -> pd.DataFrame:
    """Tendência central, dispersão, n e ausentes por versão e cenário."""

    rows: list[dict[str, Any]] = []
    for (version, scenario), group in frame.groupby(["software_version", "scenario"], dropna=False):
        version_label = "missing_version" if pd.isna(version) else str(version)
        scenario_label = "missing_scenario" if pd.isna(scenario) else str(scenario)
        for metric in metrics:
            series = group[metric] if metric in group.columns else pd.Series(dtype=float)
            total = int(len(series))
            observed = _observed(series)
            n_obs = int(observed.size)
            n_missing = total - n_obs
            catalog = METRIC_CATALOG.get(metric, {"unit": "", "scale": "ratio", "aggregation": ""})
            if n_obs == 0:
                rows.append(
                    {
                        "campaign_id": str(group["campaign_id"].iloc[0]) if len(group) else "",
                        "software_version": version_label,
                        "scenario": scenario_label,
                        "metric": metric,
                        "unit": catalog["unit"],
                        "scale": catalog["scale"],
                        "n": total,
                        "n_observed": 0,
                        "n_missing": n_missing,
                        "mean": np.nan,
                        "median": np.nan,
                        "std": np.nan,
                        "min": np.nan,
                        "q1": np.nan,
                        "q3": np.nan,
                        "iqr": np.nan,
                        "max": np.nan,
                        "notes": "sem observações válidas; ausentes não imputados",
                    }
                )
                continue

            q1, q3 = np.percentile(observed, [25, 75])
            rows.append(
                {
                    "campaign_id": str(group["campaign_id"].iloc[0]),
                    "software_version": version_label,
                    "scenario": scenario_label,
                    "metric": metric,
                    "unit": catalog["unit"],
                    "scale": catalog["scale"],
                    "n": total,
                    "n_observed": n_obs,
                    "n_missing": n_missing,
                    "mean": float(np.mean(observed)),
                    "median": float(np.median(observed)),
                    "std": float(np.std(observed, ddof=1)) if n_obs > 1 else np.nan,
                    "min": float(np.min(observed)),
                    "q1": float(q1),
                    "q3": float(q3),
                    "iqr": float(q3 - q1),
                    "max": float(np.max(observed)),
                    "notes": catalog["aggregation"],
                }
            )
    return pd.DataFrame(rows)


def complete_pairs_by_block(
    frame: pd.DataFrame,
    metrics: Iterable[str],
    *,
    versions: tuple[str, str] | None = None,
) -> pd.DataFrame:
    """Conta pares completos por bloco e cenário, preservando o identificador de bloco."""

    present_versions = sorted({str(v) for v in frame["software_version"].dropna().unique()})
    if versions is None:
        if len(present_versions) == 1:
            config = json.loads((ROOT / "config" / "collection-s02.json").read_text(encoding="utf-8"))
            versions = tuple(config["versions"])
        else:
            versions = tuple(present_versions)
        if len(versions) != 2 or not set(present_versions).issubset(versions):
            raise CompleteAnalysisError("versões incompatíveis com a comparação pareada")
        left, right = versions
    else:
        left, right = versions

    rows: list[dict[str, Any]] = []
    for (block, scenario), group in frame.groupby(["block", "scenario"], dropna=False):
        block_label = pd.NA if pd.isna(block) else int(block)
        scenario_label = "missing_scenario" if pd.isna(scenario) else str(scenario)
        left_rows = group.loc[group["software_version"].astype("string") == left]
        right_rows = group.loc[group["software_version"].astype("string") == right]
        sources = sorted({str(s) for s in group["source"].dropna().unique()})
        for metric in metrics:
            left_obs = _observed(left_rows[metric]) if metric in left_rows else np.array([])
            right_obs = _observed(right_rows[metric]) if metric in right_rows else np.array([])
            complete = bool(left_obs.size and right_obs.size)
            rows.append(
                {
                    "campaign_id": str(group["campaign_id"].iloc[0]) if len(group) else "",
                    "block": block_label,
                    "scenario": scenario_label,
                    "metric": metric,
                    "version_a": left,
                    "version_b": right,
                    "n_version_a": int(left_obs.size),
                    "n_version_b": int(right_obs.size),
                    "pair_complete": complete,
                    "value_a": float(left_obs[0]) if left_obs.size == 1 else (
                        float(np.mean(left_obs)) if left_obs.size > 1 else np.nan
                    ),
                    "value_b": float(right_obs[0]) if right_obs.size == 1 else (
                        float(np.mean(right_obs)) if right_obs.size > 1 else np.nan
                    ),
                    "sources": ";".join(sources),
                }
            )
    return pd.DataFrame(rows)


def block_trace_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Tabela de rastreabilidade: bloco, versão, cenário e caminho bruto."""

    columns = [column for column in IDENTITY_COLUMNS if column in frame.columns]
    trace = frame.loc[:, columns].copy()
    sort_columns = [column for column in (*ROUND_KEY, "position") if column in columns]
    trace = trace.sort_values(sort_columns, kind="mergesort")
    return trace.reset_index(drop=True)


def metric_catalog_frame(metrics: Iterable[str]) -> pd.DataFrame:
    rows = []
    for metric in metrics:
        info = METRIC_CATALOG.get(metric, {"unit": "", "scale": "ratio", "aggregation": ""})
        rows.append(
            {
                "metric": metric,
                "unit": info["unit"],
                "scale": info["scale"],
                "aggregation_criteria": info["aggregation"],
            }
        )
    return pd.DataFrame(rows)


def plot_metric_by_scenario(
    frame: pd.DataFrame,
    metric: str,
    output_path: Path,
    *,
    dataset_label: str,
) -> Path:
    """Boxplots por cenário, com as duas versões lado a lado."""

    if metric not in frame.columns:
        raise CompleteAnalysisError(f"métrica ausente: {metric}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scenarios = sorted({str(s) for s in frame["scenario"].dropna().unique()})
    versions = sorted({str(v) for v in frame["software_version"].dropna().unique()})
    catalog = METRIC_CATALOG.get(metric, {"unit": metric})

    fig, axes = plt.subplots(1, len(scenarios), figsize=(5.2 * len(scenarios), 4.8), squeeze=False)

    colors = ["#4c78a8", "#f58518", "#54a24b", "#e45756"]
    for axis, scenario in zip(axes[0], scenarios):
        data = []
        labels = []
        for version in versions:
            values = _observed(
                frame.loc[
                    (frame["scenario"].astype("string") == scenario)
                    & (frame["software_version"].astype("string") == version),
                    metric,
                ]
            )
            data.append(values if values.size else np.array([np.nan]))
            labels.append(version)
        boxes = axis.boxplot(data, patch_artist=True, widths=0.55)
        axis.set_xticks(range(1, len(labels) + 1), labels)
        for patch, color in zip(boxes["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.55)
        axis.set_title(scenario)
        axis.set_xlabel("Versão do PostgreSQL")
        axis.set_ylabel(f"{metric} ({catalog.get('unit', '')})")
        axis.grid(axis="y", alpha=0.3)

    fig.suptitle(f"Distribuição de {metric} por cenário — coleta completa")
    fig.text(
        0.01,
        0.01,
        f"Fonte: {dataset_label} | Ausentes excluídos do gráfico | LAB05S02 #153",
        fontsize=8,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def artifact_label(path: Path) -> str:
    resolved = path.resolve()
    repo = ROOT.parent
    return resolved.relative_to(repo).as_posix() if resolved.is_relative_to(repo) else resolved.name


def write_metric_docs(path: Path, metrics: Iterable[str], dataset_path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Critérios de agregação — análise descritiva LAB05S02",
        "",
        f"Dataset validado: `{artifact_label(dataset_path)}`",
        "",
        "A análise usa apenas rodadas presentes no CSV validado. Valores ausentes",
        "permanecem NaN, entram em `n_missing` e nunca são imputados como zero.",
        "O identificador `block` é preservado nas tabelas de pares e de rastreabilidade,",
        "com o caminho bruto em `source`.",
        "As contagens descrevem as rodadas presentes no CSV. Rodadas excluídas",
        "e pares totalmente ausentes constam do relatório de qualidade da coleta.",
        "Cada painel de distribuição usa escala vertical própria.",
        "",
        "| Métrica | Unidade | Escala | Critério de agregação |",
        "|---|---|---|---|",
    ]
    for metric in metrics:
        info = METRIC_CATALOG.get(metric, {"unit": "", "scale": "ratio", "aggregation": ""})
        lines.append(
            f"| `{metric}` | {info['unit']} | {info['scale']} | {info['aggregation']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_complete_descriptive(
    *,
    dataset_path: Path = DEFAULT_DATASET,
    tables_dir: Path = DEFAULT_TABLES,
    figures_dir: Path = DEFAULT_FIGURES,
    docs_dir: Path = DEFAULT_DOCS,
) -> dict[str, Path]:
    frame = load_validated_dataset(dataset_path)
    metrics = available_metrics(frame)
    if not metrics:
        raise CompleteAnalysisError("nenhuma métrica analisável no dataset validado")

    descriptive = descriptive_by_version_scenario(frame, metrics)
    pairs = complete_pairs_by_block(frame, metrics)
    trace = block_trace_table(frame)
    catalog = metric_catalog_frame(metrics)

    tables_dir = Path(tables_dir)
    figures_dir = Path(figures_dir)
    docs_dir = Path(docs_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    descriptive_path = tables_dir / "s02_descriptive_by_version_scenario.csv"
    pairs_path = tables_dir / "s02_complete_pairs.csv"
    pairs_summary_path = tables_dir / "s02_complete_pairs_summary.csv"
    trace_path = tables_dir / "s02_block_traceability.csv"
    catalog_path = tables_dir / "s02_metric_catalog.csv"
    summary_path = tables_dir / "s02_descriptive_summary.json"
    docs_path = docs_dir / "analise-descritiva-lab05s02.md"

    descriptive.to_csv(descriptive_path, index=False)
    pairs.to_csv(pairs_path, index=False)
    pairs_summary = (
        pairs.groupby(["scenario", "metric"], dropna=False)
        .agg(
            blocks=("block", "nunique"),
            complete_pairs=("pair_complete", "sum"),
            incomplete_pairs=("pair_complete", lambda values: int((~values.astype(bool)).sum())),
        )
        .reset_index()
    )
    pairs_summary.to_csv(pairs_summary_path, index=False)
    trace.to_csv(trace_path, index=False)
    catalog.to_csv(catalog_path, index=False)
    write_metric_docs(docs_path, metrics, Path(dataset_path))

    figure_paths = {}
    for name, metric in (("latency", "query_latency_ms"), ("throughput", "throughput_queries_per_second")):
        if metric in metrics:
            figure_paths[f"{name}_figure"] = plot_metric_by_scenario(
                frame, metric, figures_dir / f"s02_{name}_by_scenario.png",
                dataset_label=artifact_label(dataset_path),
            )

    summary = {
        "dataset": artifact_label(dataset_path),
        "campaign_id": str(frame["campaign_id"].iloc[0]),
        "n_rows": int(len(frame)),
        "n_blocks": int(frame["block"].nunique()),
        "versions": sorted({str(v) for v in frame["software_version"].dropna().unique()}),
        "scenarios": sorted({str(s) for s in frame["scenario"].dropna().unique()}),
        "metrics": metrics,
        "missing_policy": "ausentes permanecem NaN e entram em n_missing; nunca viram zero",
        "tables": {
            "descriptive": artifact_label(descriptive_path),
            "complete_pairs": artifact_label(pairs_path),
            "complete_pairs_summary": artifact_label(pairs_summary_path),
            "traceability": artifact_label(trace_path),
            "metric_catalog": artifact_label(catalog_path),
        },
        "figures": {name: artifact_label(path) for name, path in figure_paths.items()},
        "docs": artifact_label(docs_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "descriptive": descriptive_path,
        "complete_pairs": pairs_path,
        "complete_pairs_summary": pairs_summary_path,
        "traceability": trace_path,
        "metric_catalog": catalog_path,
        "summary": summary_path,
        "docs": docs_path,
        **figure_paths,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Análise descritiva da coleta completa LAB05S02")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--tables-dir", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS)
    args = parser.parse_args(argv)
    paths = run_complete_descriptive(
        dataset_path=args.dataset,
        tables_dir=args.tables_dir,
        figures_dir=args.figures_dir,
        docs_dir=args.docs_dir,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
