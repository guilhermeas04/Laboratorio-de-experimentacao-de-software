"""Analises reproduziveis das RQ03/RQ04 e classificacao DORA C1."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

LAB3_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = LAB3_ROOT / "data" / "processed" / "datasets" / "s02_metrics.csv"
DEFAULT_OUTPUT = LAB3_ROOT / "reports" / "rq03-rq04"
MONTHLY_FREQUENCY = 1 / (365 / 7)
SCORES = {"Elite": 4, "High": 3, "Medium": 2, "Low": 1}
CLASS_LABELS = ("Elite", "High", "Medium", "Low", "ausente")


@dataclass(frozen=True)
class MetricSummary:
    metric: str
    n_total: int
    n_present: int
    n_missing: int
    missing_rate: float
    median: float | None
    q1: float | None
    q3: float | None
    iqr: float | None


def read_dataset(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "repository" not in rows[0]:
        raise ValueError(f"dataset invalido ou vazio: {path}")
    return rows


def summarize_metric(rows: Sequence[dict[str, Any]], column: str, label: str) -> MetricSummary:
    values = sorted(value for value in (_as_number(row.get(column)) for row in rows) if value is not None)
    q1 = _quantile(values, 0.25)
    q3 = _quantile(values, 0.75)
    missing = len(rows) - len(values)
    return MetricSummary(label, len(rows), len(values), missing, missing / len(rows) if rows else 0.0, _quantile(values, 0.5), q1, q3, q3 - q1 if q1 is not None and q3 is not None else None)


def classify_deployment_frequency(value: float | None) -> str:
    if value is None:
        return "ausente"
    if value >= 7:
        return "Elite"
    if value >= 1:
        return "High"
    if value >= MONTHLY_FREQUENCY:
        return "Medium"
    return "Low"


def classify_lead_time(value: float | None) -> str:
    if value is None:
        return "ausente"
    if value < 1:
        return "Elite"
    if value < 7:
        return "High"
    if value < 30:
        return "Medium"
    return "Low"


def classify_cfr(value: float | None) -> str:
    if value is None:
        return "ausente"
    if value <= 0.15:
        return "Elite"
    if value <= 0.30:
        return "High"
    if value <= 0.45:
        return "Medium"
    return "Low"


def classify_recovery(value: float | None) -> str:
    if value is None:
        return "ausente"
    if value < 1:
        return "Elite"
    if value < 24:
        return "High"
    if value < 168:
        return "Medium"
    return "Low"


def classify_c1(row: dict[str, Any]) -> dict[str, Any]:
    """Classifica C1 com release frequency, lead time(a), CFR(a) e recovery."""

    frequency = _as_number(row.get("deployment_frequency_per_week"))
    lead_time = _as_number(row.get("lead_time_by_release_days"))
    cfr_a = _as_number(row.get("cfr_ci"))
    recovery = _as_number(row.get("recovery_median_hours"))
    classes = {
        "deployment_frequency_class": classify_deployment_frequency(frequency),
        "lead_time_class": classify_lead_time(lead_time),
        "cfr_a_class": classify_cfr(cfr_a),
        "recovery_class": classify_recovery(recovery),
    }
    scores = [SCORES[value] for value in classes.values() if value in SCORES]
    return {
        "repository": str(row.get("repository") or ""),
        "deployment_frequency_per_week": frequency,
        "lead_time_by_release_days": lead_time,
        "cfr_a": cfr_a,
        "cfr_b": _as_number(row.get("cfr_b")),
        "recovery_median_hours": recovery,
        **classes,
        "c1_metric_count": len(scores),
        "c1_class": _score_label(_floor_median(scores)) if len(scores) == 4 else "ausente",
        "eligible": str(row.get("eligible") or ""),
        "exclusion_reason": str(row.get("exclusion_reason") or ""),
    }


def analyze(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    specs = (("cfr_ci", "cfr_a"), ("cfr_b", "cfr_b"), ("recovery_median_hours", "recovery_median_hours"), ("recovery_censored_count", "recovery_censored_count"))
    classifications = [classify_c1(row) for row in rows]
    return {
        "repository_count": len(rows),
        "expected_repository_count": 300,
        "repository_count_matches_target": len(rows) == 300,
        "definitions": {
            "cfr_a": "falhas de workflow / (falhas + sucessos) usando conclusoes validas",
            "cfr_b": "release seguida por corretiva em ate 7 dias; ultimos 7 dias censurados",
            "recovery": "mediana em horas dos episodios encerrados; episodios sem sucesso sao censurados",
            "c1": "mediana inteira inferior das notas de frequency, lead time(a), CFR(a) e recovery",
        },
        "metrics": [asdict(summarize_metric(rows, column, label)) for column, label in specs],
        "censored_recovery_episodes": _censored_summary(rows),
        "classifications": classifications,
        "missing_repositories": _missing_rows(rows),
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rq03-rq04-c1-summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_csv(output_dir / "rq03-rq04-c1-summary.csv", result["metrics"])
    _write_csv(output_dir / "rq03-rq04-c1-classifications.csv", result["classifications"])
    _write_csv(output_dir / "rq03-rq04-c1-missing.csv", result["missing_repositories"], ("repository", "missing_metrics", "eligible", "exclusion_reason"))
    _write_markdown(result, output_dir / "rq03-rq04-c1-summary.md")
    _write_bar_chart(output_dir / "cfr-a-distribution.svg", "CFR(a) - falhas de CI", _distribution(result["classifications"], "cfr_a_class"))
    _write_bar_chart(output_dir / "cfr-b-distribution.svg", "CFR(b) - falhas de entrega", _distribution_from_values(result, "cfr_b"))
    _write_bar_chart(output_dir / "recovery-distribution.svg", "Recuperacao - horas", _distribution(result["classifications"], "recovery_class"))
    _write_bar_chart(output_dir / "dora-c1-distribution.svg", "Classificacao DORA C1", _distribution(result["classifications"], "c1_class"))


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    lines = ["# RQ03, RQ04 e DORA C1", "", f"Repositórios considerados: **{result['repository_count']}** (alvo: 300).", "Ausentes ficam fora da mediana/IQR e não são convertidos em zero.", "", "| Métrica | N válido | Ausentes | Mediana | Q1 | Q3 | IQR |", "|---|---:|---:|---:|---:|---:|---:|"]
    for item in result["metrics"]:
        lines.append(f"| {item['metric']} | {item['n_present']} | {item['n_missing']} | {_format(item['median'])} | {_format(item['q1'])} | {_format(item['q3'])} | {_format(item['iqr'])} |")
    lines.extend(["", "## Definições", "", "- CFR(a): falhas de workflow / (falhas + sucessos) válidos.", "- CFR(b): release seguida por corretiva em até 7 dias; releases dos últimos 7 dias são censuradas.", "- Recuperação: mediana em horas dos episódios encerrados; episódios sem sucesso até o fim da janela são censurados.", "- C1: deployment por release, lead time por release, CFR(a) e recuperação; a nota geral é a mediana inteira inferior das quatro notas.", "", f"Episódios de recuperação censurados: {result['censored_recovery_episodes']['episodes']} em {result['censored_recovery_episodes']['repositories_with_censored_episodes']} repositórios."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _censored_summary(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    censored = [_as_number(row.get("recovery_censored_count")) or 0 for row in rows]
    return {"episodes": int(sum(censored)), "repositories_with_censored_episodes": sum(value > 0 for value in censored)}


def _missing_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    columns = ("cfr_ci", "cfr_b", "recovery_median_hours")
    return [{"repository": str(row.get("repository") or ""), "missing_metrics": ";".join(column for column in columns if _as_number(row.get(column)) is None), "eligible": row.get("eligible", ""), "exclusion_reason": row.get("exclusion_reason", "")} for row in rows if any(_as_number(row.get(column)) is None for column in columns)]


def _distribution(rows: Iterable[dict[str, Any]], column: str) -> dict[str, int]:
    counts = {label: 0 for label in CLASS_LABELS}
    for row in rows:
        counts[str(row[column])] += 1
    return counts


def _distribution_from_values(result: dict[str, Any], column: str) -> dict[str, int]:
    counts = {label: 0 for label in CLASS_LABELS}
    for row in result["classifications"]:
        counts[classify_cfr(row.get(column))] += 1
    return counts


def _write_bar_chart(path: Path, title: str, counts: dict[str, int]) -> None:
    colors = {"Elite": "#176b87", "High": "#4f9d69", "Medium": "#e0a458", "Low": "#c94c4c", "ausente": "#9aa5b1"}
    baseline, maximum, bars = 350, max(counts.values(), default=1), []
    for index, label in enumerate(CLASS_LABELS):
        value = counts.get(label, 0)
        height = int(250 * value / maximum) if maximum else 0
        x, y = 55 + index * 130, baseline - height
        bars.extend([f'<rect x="{x}" y="{y}" width="90" height="{height}" fill="{colors[label]}"/>', f'<text x="{x + 45}" y="375" text-anchor="middle">{label}</text>', f'<text x="{x + 45}" y="{y - 8}" text-anchor="middle">{value}</text>'])
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="420"><rect width="100%" height="100%" fill="#f7f4ef"/><text x="360" y="35" text-anchor="middle" font-size="20" font-family="sans-serif">{title}</text><line x1="40" y1="350" x2="700" y2="350" stroke="#24313a"/>{"".join(bars)}</svg>\n', encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    columns = list(fieldnames or ())
    if not columns:
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _quantile(values: Sequence[float], probability: float) -> float | None:
    if not values:
        return None
    position = (len(values) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    return values[lower] if lower == upper else values[lower] + (values[upper] - values[lower]) * (position - lower)


def _floor_median(values: Sequence[int]) -> int:
    ordered = sorted(values)
    return math.floor(_quantile(ordered, 0.5) or 0)


def _score_label(score: int) -> str:
    return next(label for label, value in SCORES.items() if value == score)


def _as_number(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _format(value: float | None) -> str:
    return "" if value is None else f"{value:.4f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analisa RQ03/RQ04 e DORA C1 do dataset S02.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyze(read_dataset(args.input))
    write_outputs(result, args.output)
    print(f"RQ03/RQ04/C1: {result['repository_count']} repositorios; saidas em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())