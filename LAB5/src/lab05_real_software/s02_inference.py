"""Testes pareados e tamanho de efeito da coleta completa LAB05S02."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .s02_descriptive import DEFAULT_DATASET, ROOT, artifact_label, load_validated_dataset
from .s02_validity import _paired_rows

DEFAULT_CONFIG = ROOT / "config" / "collection-s02.json"
DEFAULT_TABLES = ROOT / "reports" / "tables"
DEFAULT_DOCS = ROOT / "docs"

LOWER_IS_BETTER = {"query_latency_ms", "cpu_percent", "memory_mb", "client_latency_ms"}
SECONDARY_METRICS = (
    "throughput_queries_per_second",
    "cpu_percent",
    "memory_mb",
    "client_latency_ms",
)


class PairedInferenceError(ValueError):
    """Indica falha na inferência pareada da coleta completa."""


def load_collection_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_file():
        raise PairedInferenceError(f"configuração não encontrada: {config_path}")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PairedInferenceError(f"JSON inválido em {config_path}: {exc.msg}") from exc
    if not isinstance(config, dict) or "primary" not in config or "versions" not in config:
        raise PairedInferenceError("collection-s02.json precisa de versions e primary")
    return config


def build_pairs(
    frame: pd.DataFrame,
    *,
    scenario: str,
    metric: str,
    versions: list[str],
) -> pd.DataFrame:
    if len(versions) != 2:
        raise PairedInferenceError("a comparação pareada exige exatamente duas versões")
    if metric not in frame.columns:
        raise PairedInferenceError(f"métrica ausente no dataset: {metric}")
    return _paired_rows(frame, scenario, metric, versions)


def shapiro_assessment(differences: np.ndarray) -> dict[str, Any]:
    values = np.asarray(differences, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 3:
        return {
            "test": "shapiro_wilk",
            "n": int(values.size),
            "statistic": None,
            "p_value": None,
            "normality_sustainable": False,
            "note": "amostra pequena demais para avaliar normalidade das diferenças",
        }
    statistic, p_value = stats.shapiro(values)
    return {
        "test": "shapiro_wilk",
        "n": int(values.size),
        "statistic": float(statistic),
        "p_value": float(p_value),
        "normality_sustainable": bool(p_value >= 0.05),
        "note": "Shapiro–Wilk não detectou desvio de normalidade das diferenças"
        if p_value >= 0.05
        else "pressuposto de normalidade questionável; inferência t registrada com ressalva",
    }


def paired_effect_size(differences: np.ndarray) -> dict[str, Any]:
    values = np.asarray(differences, dtype=float)
    values = values[np.isfinite(values)]
    n = int(values.size)
    if n < 2:
        return {"effect_size_name": "cohens_dz", "cohens_dz": None, "n_pairs": n, "defined": False}
    std = float(np.std(values, ddof=1))
    if std == 0:
        return {
            "effect_size_name": "cohens_dz",
            "cohens_dz": None,
            "n_pairs": n,
            "defined": False,
            "reason": "variância zero nas diferenças pareadas",
        }
    return {
        "effect_size_name": "cohens_dz",
        "cohens_dz": float(np.mean(values) / std),
        "n_pairs": n,
        "defined": True,
    }


def paired_t_analysis(
    pairs: pd.DataFrame,
    *,
    metric: str,
    alpha: float = 0.05,
    alternative: str = "two-sided",
    role: str = "primary",
) -> dict[str, Any]:
    """Executa o contraste pareado pré-especificado e registra insuficiência."""

    if alternative != "two-sided" or not 0 < alpha < 1:
        raise PairedInferenceError("o protocolo exige alternativa bilateral e 0 < alfa < 1")
    differences = pairs["difference_a_minus_b"].to_numpy(dtype=float) if not pairs.empty else np.array([])
    n_pairs = int(differences.size)
    mean_a = float(pairs["value_a"].mean()) if n_pairs else None
    mean_b = float(pairs["value_b"].mean()) if n_pairs else None
    mean_diff = float(np.mean(differences)) if n_pairs else None
    std_diff = float(np.std(differences, ddof=1)) if n_pairs >= 2 else None

    result: dict[str, Any] = {
        "role": role,
        "metric": metric,
        "n_pairs": n_pairs,
        "mean_version_a": mean_a,
        "mean_version_b": mean_b,
        "mean_difference_a_minus_b": mean_diff,
        "std_difference": std_diff,
        "alpha": alpha,
        "alternative": alternative,
        "test_name": "paired_t",
        "statistic": None,
        "df": None,
        "p_value": None,
        "ci_low": None,
        "ci_high": None,
        "reject_null": None,
        "inference_status": "ok",
        "assumption_check": None,
        "effect_size": None,
        "notes": [],
    }

    if n_pairs < 3:
        result["inference_status"] = "insufficient"
        result["assumption_check"] = shapiro_assessment(differences)
        result["notes"].append("menos de três pares completos; normalidade não avaliável")
        result["effect_size"] = paired_effect_size(differences)
        return result

    if std_diff == 0:
        result["inference_status"] = "insufficient"
        result["notes"].append("variância zero nas diferenças; teste t e d_z indefinidos")
        result["effect_size"] = paired_effect_size(differences)
        return result

    assumption = shapiro_assessment(differences)
    result["assumption_check"] = assumption
    if not assumption["normality_sustainable"]:
        result["notes"].append(assumption["note"])

    t_result = stats.ttest_1samp(differences, popmean=0.0, alternative=alternative)
    df = n_pairs - 1
    se = std_diff / np.sqrt(n_pairs)
    t_crit = float(stats.t.ppf(1 - alpha / 2, df))
    ci_low = mean_diff - t_crit * se
    ci_high = mean_diff + t_crit * se
    p_value = float(t_result.pvalue)

    result.update(
        {
            "statistic": float(t_result.statistic),
            "df": int(df),
            "p_value": p_value,
            "ci_low": float(ci_low),
            "ci_high": float(ci_high),
            "reject_null": bool(p_value < alpha) if assumption["normality_sustainable"] else None,
            "effect_size": paired_effect_size(differences),
        }
    )
    if not assumption["normality_sustainable"]:
        result["inference_status"] = "assumption_warning"
        wilcoxon = stats.wilcoxon(differences, alternative=alternative)
        result["exploratory_wilcoxon"] = {
            "statistic": float(wilcoxon.statistic),
            "p_value": float(wilcoxon.pvalue),
            "note": "análise exploratória de postos sinalizados, que pressupõe simetria das diferenças",
        }
    return result


def practical_relevance(
    *,
    mean_version_a: float | None,
    mean_difference: float | None,
    metric: str,
    minimum_relative_reduction: float,
) -> dict[str, Any]:
    if mean_version_a is None or mean_difference is None or mean_version_a == 0:
        return {
            "minimum_relative_reduction": minimum_relative_reduction,
            "observed_relative_change": None,
            "practical_threshold_absolute": None,
            "interpretation": "indeterminate",
            "note": "não foi possível comparar com o ganho mínimo definido",
        }

    if metric in LOWER_IS_BETTER:
        # diferença a-b > 0 favorece a versão B (17) quando menor é melhor
        observed_relative = mean_difference / mean_version_a
        threshold_abs = minimum_relative_reduction * mean_version_a
        met = observed_relative >= minimum_relative_reduction
        direction = "reduction_favoring_version_b"
    else:
        observed_relative = -mean_difference / mean_version_a
        threshold_abs = minimum_relative_reduction * mean_version_a
        met = observed_relative >= minimum_relative_reduction
        direction = "increase_favoring_version_b"

    return {
        "minimum_relative_reduction": minimum_relative_reduction,
        "observed_relative_change": float(observed_relative),
        "observed_relative_change_percent": float(100 * observed_relative),
        "practical_threshold_absolute": float(threshold_abs),
        "mean_difference_a_minus_b": float(mean_difference),
        "direction": direction,
        "interpretation": "threshold_met" if met else "threshold_not_met",
        "note": (
            "relevância prática avaliada contra o limiar pré-especificado de "
            f"{100 * minimum_relative_reduction:.0f}% da média da versão A"
        ),
    }


def holm_adjust(p_values: list[float | None]) -> list[float | None]:
    indexed = [(index, p) for index, p in enumerate(p_values) if p is not None]
    adjusted = [None] * len(p_values)
    if not indexed:
        return adjusted
    indexed.sort(key=lambda item: item[1])
    m = len(indexed)
    running = 0.0
    holm_values = [0.0] * m
    for rank, (_, p_value) in enumerate(indexed):
        candidate = (m - rank) * p_value
        running = max(running, candidate)
        holm_values[rank] = min(1.0, running)
    # enforce monotonicity from the largest p upward
    for rank in range(m - 2, -1, -1):
        holm_values[rank] = min(holm_values[rank], holm_values[rank + 1])
    for rank, (index, _) in enumerate(indexed):
        adjusted[index] = float(holm_values[rank])
    return adjusted


def analyze_secondary(
    frame: pd.DataFrame,
    *,
    versions: list[str],
    primary_scenario: str,
    primary_metric: str,
    alpha: float,
    alternative: str,
) -> list[dict[str, Any]]:
    scenarios = sorted({str(value) for value in frame["scenario"].dropna().unique()})
    metrics = [metric for metric in SECONDARY_METRICS if metric in frame.columns]
    # também inclui a métrica primária em cenários não primários
    if primary_metric in frame.columns:
        metrics = list(dict.fromkeys([primary_metric, *metrics]))

    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        for metric in metrics:
            if scenario == primary_scenario and metric == primary_metric:
                continue
            pairs = build_pairs(frame, scenario=scenario, metric=metric, versions=versions)
            analysis = paired_t_analysis(
                pairs,
                metric=metric,
                alpha=alpha,
                alternative=alternative,
                role="secondary_exploratory",
            )
            analysis["scenario"] = scenario
            analysis["versions"] = versions
            rows.append(analysis)

    p_values = [row.get("p_value") for row in rows]
    adjusted = holm_adjust(p_values)
    for row, adj in zip(rows, adjusted):
        row["p_value_holm"] = adj
        row["multiple_comparison"] = "holm"
        if adj is None or row["inference_status"] != "ok":
            row["reject_null_holm"] = None
        else:
            row["reject_null_holm"] = bool(adj < alpha)
    return rows


def run_paired_inference(
    *,
    dataset_path: Path = DEFAULT_DATASET,
    config_path: Path = DEFAULT_CONFIG,
    tables_dir: Path = DEFAULT_TABLES,
    docs_dir: Path = DEFAULT_DOCS,
) -> dict[str, Path]:
    config = load_collection_config(config_path)
    frame = load_validated_dataset(dataset_path)
    versions = [str(value) for value in config["versions"]]
    primary = config["primary"]
    scenario = str(primary["scenario"])
    metric = str(primary["metric"])
    alpha = float(primary.get("alpha", 0.05))
    alternative = str(primary.get("alternative", "two-sided"))
    minimum_relative = float(primary.get("minimum_relative_reduction", 0.1))

    pairs = build_pairs(frame, scenario=scenario, metric=metric, versions=versions)
    primary_result = paired_t_analysis(
        pairs,
        metric=metric,
        alpha=alpha,
        alternative=alternative,
        role="primary",
    )
    primary_result["scenario"] = scenario
    primary_result["versions"] = versions
    primary_result["practical_relevance"] = practical_relevance(
        mean_version_a=primary_result["mean_version_a"],
        mean_difference=primary_result["mean_difference_a_minus_b"],
        metric=metric,
        minimum_relative_reduction=minimum_relative,
    )

    secondary_results = analyze_secondary(
        frame,
        versions=versions,
        primary_scenario=scenario,
        primary_metric=metric,
        alpha=alpha,
        alternative=alternative,
    )

    tables_dir = Path(tables_dir)
    docs_dir = Path(docs_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    pairs_path = tables_dir / "s02_paired_primary_differences.csv"
    primary_path = tables_dir / "s02_paired_primary_inference.json"
    secondary_path = tables_dir / "s02_paired_secondary_inference.csv"
    summary_path = tables_dir / "s02_paired_inference_summary.json"
    docs_path = docs_dir / "inferencia-pareada-lab05s02.md"

    export_pairs = pairs.copy()
    export_pairs["version_a"] = versions[0]
    export_pairs["version_b"] = versions[1]
    export_pairs["scenario"] = scenario
    export_pairs["metric"] = metric
    export_pairs.to_csv(pairs_path, index=False)

    primary_path.write_text(json.dumps(primary_result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    secondary_frame = pd.json_normalize(secondary_results)
    secondary_frame.to_csv(secondary_path, index=False)

    summary = {
        "dataset": artifact_label(dataset_path),
        "config": artifact_label(config_path),
        "primary": primary_result,
        "secondary_count": len(secondary_results),
        "reproduction": {
            "command": (
                "PYTHONPATH=LAB5/src python -m lab05_real_software.s02_inference "
                "--dataset LAB5/data/processed/lab05s02-20261121-01_validated.csv"
            )
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    docs_path.write_text(_render_docs(primary_result, secondary_results, versions), encoding="utf-8")

    return {
        "pairs": pairs_path,
        "primary": primary_path,
        "secondary": secondary_path,
        "summary": summary_path,
        "docs": docs_path,
    }


def _render_docs(primary: dict[str, Any], secondary: list[dict[str, Any]], versions: list[str]) -> str:
    practical = primary.get("practical_relevance") or {}
    effect = primary.get("effect_size") or {}
    lines = [
        "# Inferência pareada — LAB05S02",
        "",
        "Contraste pré-especificado no desenho da Sprint 2:",
        "",
        f"- versões: `{versions[0]}` (A) versus `{versions[1]}` (B);",
        f"- cenário/métrica primários: `{primary.get('scenario')}` / `{primary.get('metric')}`;",
        "- unidade de análise: bloco pareado;",
        "- H0: diferença média pareada igual a zero; alternativa bilateral; alfa = 0,05;",
        "- teste confirmatório: t pareado, quando os pressupostos forem sustentáveis;",
        "- demais métricas/cenários: exploratórios, com ajuste de Holm.",
        "",
        "## Resultado primário",
        "",
        f"- pares completos: **{primary.get('n_pairs')}**;",
        f"- diferença média A−B: **{primary.get('mean_difference_a_minus_b')}**;",
        f"- IC 95%: **[{primary.get('ci_low')}, {primary.get('ci_high')}]**;",
        f"- p-valor: **{primary.get('p_value')}**;",
        f"- status da inferência: **{primary.get('inference_status')}**;",
        f"- Cohen d_z: **{effect.get('cohens_dz')}**;",
        f"- relevância prática (≥ {100 * float(practical.get('minimum_relative_reduction') or 0):.0f}%): "
        f"**{practical.get('interpretation')}** "
        f"(mudança relativa observada = {practical.get('observed_relative_change_percent')}%).",
        "",
        "## Métricas secundárias",
        "",
        f"Foram avaliados {len(secondary)} contrastes exploratórios. "
        "Os p-valores ajustados por Holm estão em `reports/tables/s02_paired_secondary_inference.csv`.",
        "",
        "## Leitura",
        "",
        "O teste t e seu intervalo são apresentados com ressalva quando "
        "Shapiro–Wilk aponta desvio de normalidade. Nesse caso, a decisão "
        "confirmatória fica indeterminada e Wilcoxon é apresentado como "
        "sensibilidade exploratória. A avaliação de normalidade não verifica "
        "independência entre os blocos.",
        "",
        "A relevância prática compara a estimativa pontual ao limiar "
        "definido antes da coleta. Consulte os [diagnósticos de validade]"
        "(validade-lab05s02.md) para a estabilidade por ordem e bloco.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Testes pareados e tamanho de efeito LAB05S02")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--tables-dir", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS)
    args = parser.parse_args(argv)
    paths = run_paired_inference(
        dataset_path=args.dataset,
        config_path=args.config,
        tables_dir=args.tables_dir,
        docs_dir=args.docs_dir,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
