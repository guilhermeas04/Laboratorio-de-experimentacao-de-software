"""Analises reproduziveis das RQ01 e RQ02 sobre o dataset S02."""

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
DEFAULT_OUTPUT = LAB3_ROOT / "reports" / "rq01-rq02"
WEEKS_IN_2025 = 365 / 7
MONTHLY_FREQUENCY = 1 / WEEKS_IN_2025


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
    values = [_as_number(row.get(column)) for row in rows]
    present = sorted(value for value in values if value is not None)
    q1 = _quantile(present, 0.25)
    q3 = _quantile(present, 0.75)
    median = _quantile(present, 0.5)
    missing = len(values) - len(present)
    return MetricSummary(
        metric=label,
        n_total=len(rows),
        n_present=len(present),
        n_missing=missing,
        missing_rate=missing / len(rows) if rows else 0.0,
        median=median,
        q1=q1,
        q3=q3,
        iqr=q3 - q1 if q1 is not None and q3 is not None else None,
    )


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


def classify_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    classified = []
    for row in rows:
        frequency = _as_number(row.get("deployment_frequency_per_week"))
        release_lead = _as_number(row.get("lead_time_by_release_days"))
        commit_lead = _as_number(row.get("lead_time_by_commit_days"))
        classified.append(
            {
                "repository": str(row.get("repository") or ""),
                "deployment_frequency_per_week": frequency,
                "deployment_frequency_class": classify_deployment_frequency(frequency),
                "lead_time_by_release_days": release_lead,
                "lead_time_by_release_class": classify_lead_time(release_lead),
                "lead_time_by_commit_days": commit_lead,
                "lead_time_by_commit_class": classify_lead_time(commit_lead),
                "eligible": str(row.get("eligible") or ""),
                "exclusion_reason": str(row.get("exclusion_reason") or ""),
            }
        )
    return classified


def analyze(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    summaries = [
        summarize_metric(rows, "deployment_frequency_per_week", "deployment_frequency_per_week"),
        summarize_metric(rows, "lead_time_by_release_days", "lead_time_by_release_days"),
        summarize_metric(rows, "lead_time_by_commit_days", "lead_time_by_commit_days"),
    ]
    classified = classify_rows(rows)
    return {
        "repository_count": len(rows),
        "expected_repository_count": 300,
        "repository_count_matches_target": len(rows) == 300,
        "monthly_frequency_threshold_per_week": MONTHLY_FREQUENCY,
        "metrics": [asdict(summary) for summary in summaries],
        "classifications": classified,
        "missing_repositories": [
            {
                "repository": row["repository"],
                "missing_metrics": [
                    column for column in (
                        "deployment_frequency_per_week",
                        "lead_time_by_release_days",
                        "lead_time_by_commit_days",
                    ) if _as_number(row.get(column)) is None
                ],
                "eligible": row.get("eligible", ""),
                "exclusion_reason": row.get("exclusion_reason", ""),
            }
            for row in rows
            if any(_as_number(row.get(column)) is None for column in (
                "deployment_frequency_per_week",
                "lead_time_by_release_days",
                "lead_time_by_commit_days",
            ))
        ],
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rq01-rq02-summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summaries = result["metrics"]
    _write_csv(output_dir / "rq01-rq02-summary.csv", summaries)
    _write_csv(output_dir / "rq01-rq02-classifications.csv", result["classifications"])
    _write_csv(
        output_dir / "rq01-rq02-missing.csv",
        result["missing_repositories"],
        fieldnames=("repository", "missing_metrics", "eligible", "exclusion_reason"),
    )
    _write_markdown(result, output_dir / "rq01-rq02-summary.md")
    _write_bar_chart(
        output_dir / "deployment-frequency-distribution.svg",
        "Deployment frequency (releases/semana)",
        _distribution(result["classifications"], "deployment_frequency_class"),
    )
    _write_bar_chart(
        output_dir / "lead-time-by-release-distribution.svg",
        "Lead time por release (dias)",
        _distribution(result["classifications"], "lead_time_by_release_class"),
    )
    _write_bar_chart(
        output_dir / "lead-time-by-commit-distribution.svg",
        "Lead time por commit (dias)",
        _distribution(result["classifications"], "lead_time_by_commit_class"),
    )


def _write_markdown(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# RQ01 e RQ02",
        "",
        f"Repositórios considerados: **{result['repository_count']}** (alvo: 300).",
        "Valores ausentes não foram convertidos em zero e ficam fora das estatísticas da métrica.",
        "",
        "| Métrica | N válido | Ausentes | Mediana | Q1 | Q3 | IQR |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in result["metrics"]:
        lines.append(
            f"| {item['metric']} | {item['n_present']} | {item['n_missing']} | "
            f"{_format(item['median'])} | {_format(item['q1'])} | {_format(item['q3'])} | {_format(item['iqr'])} |"
        )
    lines.extend([
        "",
        "## Classificação",
        "",
        "Cortes aplicados: deployment frequency `< 1/mês`, `1/mês a < 1/semana`, "
        "`1 a < 7/semana`, `>= 7/semana`; lead time `< 1`, `1 a < 7`, `7 a < 30`, `>= 30` dias.",
        "Repositórios sem valor recebem `ausente` e não são classificados como Low.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_bar_chart(path: Path, title: str, counts: dict[str, int]) -> None:
    colors = {"Elite": "#176b87", "High": "#4f9d69", "Medium": "#e0a458", "Low": "#c94c4c", "ausente": "#9aa5b1"}
    width, height, baseline, bar_width = 720, 420, 350, 90
    maximum = max(counts.values(), default=1)
    bars = []
    labels = ["Elite", "High", "Medium", "Low", "ausente"]
    for index, label in enumerate(labels):
        value = counts.get(label, 0)
        bar_height = int(250 * value / maximum) if maximum else 0
        x = 55 + index * 130
        y = baseline - bar_height
        bars.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{colors[label]}"/>')
        bars.append(f'<text x="{x + bar_width / 2}" y="{baseline + 25}" text-anchor="middle">{label}</text>')
        bars.append(f'<text x="{x + bar_width / 2}" y="{y - 8}" text-anchor="middle">{value}</text>')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="#f7f4ef"/><text x="360" y="35" text-anchor="middle" font-size="20" font-family="sans-serif">{title}</text>'
        f'<line x1="40" y1="{baseline}" x2="700" y2="{baseline}" stroke="#24313a"/>'
        + "".join(bars)
        + '</svg>\n'
    )
    path.write_text(svg, encoding="utf-8")


def _distribution(rows: Iterable[dict[str, Any]], column: str) -> dict[str, int]:
    counts = {label: 0 for label in ("Elite", "High", "Medium", "Low", "ausente")}
    for row in rows:
        counts[str(row[column])] += 1
    return counts


def _write_csv(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    if fieldnames is not None:
        columns = list(fieldnames)
    else:
        columns = []
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
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def _as_number(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _format(value: float | None) -> str:
    return "" if value is None else f"{value:.4f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analisa RQ01 e RQ02 do dataset S02.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyze(read_dataset(args.input))
    write_outputs(result, args.output)
    print(f"RQ01/RQ02: {result['repository_count']} repositorios; saidas em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())