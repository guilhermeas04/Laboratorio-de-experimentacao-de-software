"""Análise descritiva e tamanho de efeito do piloto LAB05S01."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .config_loader import load_study_config

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STUDY = ROOT / "config" / "study.json"
DEFAULT_METRICS = ROOT / "data" / "interim" / "pilot_metrics.csv"
DEFAULT_TABLES = ROOT / "reports" / "tables"

# Métricas do estudo (escala razão) + duração bruta do coletor piloto.
RATIO_METRICS = (
    "query_latency_ms",
    "throughput_queries_per_second",
    "cpu_percent",
    "memory_mb",
    "duration_ms",
)

METRIC_UNITS = {
    "query_latency_ms": "ms",
    "throughput_queries_per_second": "queries/s",
    "cpu_percent": "%",
    "memory_mb": "MB",
    "duration_ms": "ms",
}


class PilotAnalysisError(ValueError):
    """Indica dados ou parâmetros inválidos para a análise piloto."""


def metric_names_from_config(study_config: dict[str, Any]) -> list[str]:
    metrics = study_config["study"]["metrics"]
    names = [item["name"] for item in metrics]
    if not names:
        raise PilotAnalysisError("study.metrics não pode ser vazio")
    return names


def load_pilot_metrics(path: str | Path) -> pd.DataFrame:
    """Carrega a tabela de métricas do piloto sem preencher ausentes."""

    metrics_path = Path(path)
    if not metrics_path.is_file():
        raise PilotAnalysisError(f"arquivo de métricas não encontrado: {metrics_path}")

    frame = pd.read_csv(metrics_path, dtype={"software_version": "string"})
    if "software_version" not in frame.columns:
        raise PilotAnalysisError("coluna obrigatória ausente: software_version")

    # Garante que colunas numéricas existentes não convertam strings vazias em zero.
    for column in frame.columns:
        if column in RATIO_METRICS or column.endswith("_ms") or column.endswith("_mb"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def available_metrics(frame: pd.DataFrame, candidates: Iterable[str] | None = None) -> list[str]:
    names = list(candidates) if candidates is not None else list(RATIO_METRICS)
    return [name for name in names if name in frame.columns]


def _observed(series: pd.Series) -> np.ndarray:
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    return values[np.isfinite(values)]


def version_mask(frame: pd.DataFrame, version: str) -> pd.Series:
    labels = frame["software_version"].astype("string")
    if "." not in version:
        labels = labels.str.split(".").str[0]
    return labels == version


def paired_values(
    frame: pd.DataFrame, metric: str, baseline: str, treatment: str
) -> pd.DataFrame:
    groups = []
    for version in (baseline, treatment):
        group = frame.loc[version_mask(frame, version), ["block", metric]].set_index("block")
        if group.index.has_duplicates or group.index.isna().any():
            raise PilotAnalysisError(f"blocos ausentes ou duplicados para a versão {version}")
        values = pd.to_numeric(group[metric], errors="coerce")
        groups.append(values.where(np.isfinite(values)).rename(version))
    return pd.concat(groups, axis=1, join="inner").dropna()


def descriptive_stats(frame: pd.DataFrame, metrics: Iterable[str]) -> pd.DataFrame:
    """Estatísticas por versão e métrica, preservando ausentes como contagem explícita.

    Para métricas de escala razão usamos média, mediana, desvio-padrão, mínimo,
    máximo e IQR. Ausentes entram em n_missing e nunca são trocados por zero.
    """

    rows: list[dict[str, Any]] = []
    metric_names = list(metrics)
    if not metric_names:
        raise PilotAnalysisError("nenhuma métrica disponível para análise")

    for version, group in frame.groupby("software_version", dropna=False):
        version_label = "missing_version" if pd.isna(version) else str(version)
        for metric in metric_names:
            series = group[metric] if metric in group.columns else pd.Series(dtype=float)
            total = int(len(series))
            observed = _observed(series)
            n_obs = int(observed.size)
            n_missing = total - n_obs
            if n_obs == 0:
                rows.append(
                    {
                        "software_version": version_label,
                        "metric": metric,
                        "unit": METRIC_UNITS.get(metric, ""),
                        "n": total,
                        "n_observed": 0,
                        "n_missing": n_missing,
                        "mean": np.nan,
                        "median": np.nan,
                        "std": np.nan,
                        "min": np.nan,
                        "max": np.nan,
                        "iqr": np.nan,
                        "scale": "ratio",
                        "notes": "sem observações válidas; ausentes não foram imputados",
                    }
                )
                continue

            q1, q3 = np.percentile(observed, [25, 75])
            rows.append(
                {
                    "software_version": version_label,
                    "metric": metric,
                    "unit": METRIC_UNITS.get(metric, ""),
                    "n": total,
                    "n_observed": n_obs,
                    "n_missing": n_missing,
                    "mean": float(np.mean(observed)),
                    "median": float(np.median(observed)),
                    "std": float(np.std(observed, ddof=1)) if n_obs > 1 else np.nan,
                    "min": float(np.min(observed)),
                    "max": float(np.max(observed)),
                    "iqr": float(q3 - q1),
                    "scale": "ratio",
                    "notes": "média/mediana/desvio em escala razão; missing explícito",
                }
            )
    return pd.DataFrame(rows)


def cohens_d(sample_a: np.ndarray, sample_b: np.ndarray) -> float:
    a = np.asarray(sample_a, dtype=float)
    b = np.asarray(sample_b, dtype=float)
    if a.size < 2 or b.size < 2:
        return float("nan")
    var_a = np.var(a, ddof=1)
    var_b = np.var(b, ddof=1)
    pooled = np.sqrt(((a.size - 1) * var_a + (b.size - 1) * var_b) / (a.size + b.size - 2))
    if pooled == 0:
        return float("nan")
    return float((np.mean(a) - np.mean(b)) / pooled)


def effect_sizes(
    frame: pd.DataFrame,
    metrics: Iterable[str],
    *,
    baseline_version: str = "15",
    treatment_version: str = "17",
) -> pd.DataFrame:
    """Cohen's d para amostras independentes ou d_z para blocos pareados."""

    rows: list[dict[str, Any]] = []
    for metric in metrics:
        if metric not in frame.columns:
            continue
        baseline = _observed(frame.loc[version_mask(frame, baseline_version), metric])
        treatment = _observed(frame.loc[version_mask(frame, treatment_version), metric])
        paired = "block" in frame
        n_pairs = None
        if paired:
            pairs = paired_values(frame, metric, baseline_version, treatment_version)
            n_pairs = len(pairs)
            differences = pairs[baseline_version] - pairs[treatment_version]
            mean_difference = differences.mean()
            std = differences.std()
            d = mean_difference / std if n_pairs >= 2 and std > 0 else np.nan
        else:
            mean_difference = baseline.mean() - treatment.mean() if baseline.size and treatment.size else np.nan
            d = cohens_d(baseline, treatment)
        direction = "indefinido"
        if not np.isnan(d):
            if metric in {"query_latency_ms", "duration_ms", "cpu_percent", "memory_mb"}:
                direction = "favoravel_17" if d > 0 else "favoravel_15" if d < 0 else "neutro"
            else:
                # throughput maior é melhor
                direction = "favoravel_17" if d < 0 else "favoravel_15" if d > 0 else "neutro"
        rows.append(
            {
                "metric": metric,
                "unit": METRIC_UNITS.get(metric, ""),
                "baseline_version": baseline_version,
                "treatment_version": treatment_version,
                "n_baseline": int(baseline.size),
                "n_treatment": int(treatment.size),
                "n_pairs": n_pairs,
                "mean_difference": mean_difference,
                "mean_baseline": float(np.mean(baseline)) if baseline.size else np.nan,
                "mean_treatment": float(np.mean(treatment)) if treatment.size else np.nan,
                "cohens_d": d,
                "effect_size_name": "cohens_dz" if paired else "cohens_d",
                "direction_hint": direction,
                "notes": "pares completos; d_z usa o desvio das diferenças" if paired else
                "observações disponíveis; d usa o desvio combinado",
            }
        )
    return pd.DataFrame(rows)


def run_pilot_analysis(
    *,
    metrics_path: Path,
    study_path: Path = DEFAULT_STUDY,
    tables_dir: Path = DEFAULT_TABLES,
) -> dict[str, Path]:
    study = load_study_config(study_path)
    frame = load_pilot_metrics(metrics_path)
    configured = metric_names_from_config(study)
    metrics = available_metrics(frame, configured + ["duration_ms"])
    if not metrics:
        raise PilotAnalysisError("o arquivo de métricas não contém colunas analisáveis")

    versions = [str(v) for v in study["software"]["versions"]]
    baseline, treatment = versions[0], versions[1]

    descriptive = descriptive_stats(frame, metrics)
    effects = effect_sizes(frame, metrics, baseline_version=baseline, treatment_version=treatment)

    tables_dir = Path(tables_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    descriptive_path = tables_dir / "pilot_descriptive_stats.csv"
    effects_path = tables_dir / "pilot_effect_sizes.csv"
    summary_path = tables_dir / "pilot_analysis_summary.json"

    descriptive.to_csv(descriptive_path, index=False)
    effects.to_csv(effects_path, index=False)
    summary = {
        "software": study["software"]["name"],
        "versions": versions,
        "metrics": metrics,
        "n_rows": int(len(frame)),
        "missing_policy": "ausentes permanecem NaN e entram em n_missing; nunca viram zero",
        "descriptive_table": str(descriptive_path),
        "effect_size_table": str(effects_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "descriptive": descriptive_path,
        "effect_sizes": effects_path,
        "summary": summary_path,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Análise descritiva e efeito do piloto LAB05S01")
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--study", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--tables-dir", type=Path, default=DEFAULT_TABLES)
    args = parser.parse_args(argv)
    paths = run_pilot_analysis(metrics_path=args.metrics, study_path=args.study, tables_dir=args.tables_dir)
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
