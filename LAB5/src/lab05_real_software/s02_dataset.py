"""Validate and transform the complete LAB05S02 PostgreSQL campaign."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).parents[2]
METRIC_NAMES = (
    "query_latency_ms",
    "throughput_queries_per_second",
    "cpu_percent",
    "memory_mb",
    "client_latency_ms",
    "resource_window_seconds",
)


class CampaignValidationError(ValueError):
    """Raised when the campaign cannot be safely transformed."""


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise CampaignValidationError(f"{field} must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CampaignValidationError(f"invalid timestamp in {field}: {value}") from exc
    if parsed.tzinfo is None:
        raise CampaignValidationError(f"{field} must include a timezone")
    return parsed


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def metric_ranges(config: dict) -> dict[str, tuple[float, float]]:
    cpus = config.get("cpus")
    cpu_max = float(cpus) * 100 if _finite_number(cpus) and float(cpus) > 0 else 100.0
    return {
        "query_latency_ms": (0.0, 60_000.0),
        "throughput_queries_per_second": (0.0, float("inf")),
        "cpu_percent": (0.0, cpu_max),
        "memory_mb": (0.0, float("inf")),
        "client_latency_ms": (0.0, 60_000.0),
        "resource_window_seconds": (0.0, float("inf")),
    }


def validate_campaign(campaign_dir: str | Path) -> tuple[dict, list[dict], list[dict]]:
    """Validate a campaign directory and return manifest, accepted rows and failures."""
    directory = Path(campaign_dir)
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise CampaignValidationError(f"campaign manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("schema_version") != "lab05-s02-campaign-v1":
        raise CampaignValidationError("unsupported campaign schema_version")
    if manifest.get("status") != "complete":
        raise CampaignValidationError("campaign is not complete")

    config = manifest["configuration"]
    ranges = metric_ranges(config)
    planned = manifest["planned_rounds"]
    planned_keys = {
        (item["block"], item["scenario"], item["software_version"])
        for item in planned
    }
    accepted_attempts = {attempt["block"] for attempt in manifest["attempts"] if attempt["status"] == "accepted"}

    rows: list[dict] = []
    failures: list[dict] = []
    duplicate_keys: set[tuple] = set()

    for attempt in manifest["attempts"]:
        if attempt["status"] != "accepted":
            continue
        for entry in attempt["records"]:
            relative = entry["file"]
            path = directory / relative
            if not path.is_file():
                failures.append({"source": relative, "reason": "missing raw record", "classification": "missing"})
                continue
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append({"source": relative, "reason": f"invalid JSON: {exc.msg}", "classification": "invalid"})
                continue

            reasons: list[str] = []
            if record.get("schema_version") != "lab05-s02-round-v1":
                reasons.append("unsupported round schema_version")
            if record.get("campaign_id") != manifest["campaign_id"]:
                reasons.append("campaign_id differs from manifest")
            if record.get("execution_id") != attempt["execution_id"]:
                reasons.append("execution_id differs from manifest")
            if record.get("configuration") != config:
                reasons.append("configuration differs from manifest")
            if record.get("status") != "success":
                reasons.append(record.get("error") or "round status is not success")

            key = (record.get("block"), record.get("scenario"), record.get("software_version"))
            if key not in planned_keys:
                reasons.append("record does not belong to the planned campaign")

            if key in {(r["block"], r["scenario"], r["software_version"]) for r in rows}:
                duplicate_keys.add(key)
                reasons.append("duplicate block/scenario/version record")

            try:
                collected = _timestamp(record.get("collected_at"), "collected_at")
                ended = _timestamp(record["ended_at"], "ended_at")
                if ended < collected:
                    reasons.append("ended_at precedes collected_at")
            except (KeyError, CampaignValidationError) as exc:
                reasons.append(str(exc))

            server_version = record.get("server_version")
            configured_version = record.get("software_version")
            if not isinstance(server_version, str) or not isinstance(configured_version, str):
                reasons.append("server_version or software_version has invalid type")
            elif not server_version.startswith(configured_version):
                reasons.append("server version differs from configured version")

            if record.get("round_id") != path.stem:
                reasons.append("round_id differs from raw filename")
            if record.get("image_id") != manifest["environment"].get("images", {}).get(configured_version):
                reasons.append("PostgreSQL image differs from manifest")

            metrics = record.get("metrics")
            if not isinstance(metrics, dict):
                reasons.append("metrics must be a JSON object")
                metrics = {}
            for metric in METRIC_NAMES:
                value = metrics.get(metric)
                if not _finite_number(value):
                    reasons.append(f"{metric} missing or not a finite number")
                    continue
                low, high = ranges[metric]
                if float(value) < low or float(value) > high:
                    reasons.append(f"{metric} outside [{low:g}, {high:g}] range")

            if not isinstance(record.get("position"), int) or isinstance(record.get("position"), bool):
                reasons.append("position must be an integer")
            if not isinstance(record.get("block"), int) or isinstance(record.get("block"), bool):
                reasons.append("block must be an integer")

            if reasons:
                failures.append({
                    "source": relative,
                    "reason": "; ".join(sorted(set(reasons))),
                    "classification": "invalid",
                })
                continue

            rows.append({
                "campaign_id": manifest["campaign_id"],
                "block": record["block"],
                "position": record["position"],
                "software_version": record["software_version"],
                "scenario": record["scenario"],
                "collected_at": record["collected_at"],
                "ended_at": record["ended_at"],
                "execution_id": record["execution_id"],
                "round_id": record["round_id"],
                "source": relative,
                **{metric: metrics[metric] for metric in METRIC_NAMES},
            })

    rows.sort(key=lambda row: (row["block"], row["scenario"], row["software_version"]))
    return manifest, rows, failures


def write_processed_dataset(campaign_dir: str | Path, output_dir: str | Path | None = None) -> dict:
    """Write the validated CSV and quality reports for a campaign."""
    campaign_dir = Path(campaign_dir)
    manifest, rows, failures = validate_campaign(campaign_dir)
    if output_dir is None:
        output_dir = LAB_ROOT / "data" / "processed"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fieldnames = (
        "campaign_id", "block", "position", "software_version", "scenario",
        "collected_at", "ended_at", "execution_id", "round_id", "source",
        *METRIC_NAMES,
    )
    dataset_path = output_dir / f"{manifest['campaign_id']}_validated.csv"
    with dataset_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    missing_by_metric = {metric: sum(row[metric] is None for row in rows) for metric in METRIC_NAMES}
    # Pairs require both versions for the same block and scenario, per metric.
    pairs: dict[tuple[int, str], dict[str, set[str]]] = {}
    for row in rows:
        pair = pairs.setdefault((row["block"], row["scenario"]), {metric: set() for metric in METRIC_NAMES})
        for metric in METRIC_NAMES:
            if row[metric] is not None:
                pair[metric].add(row["software_version"])

    incomplete: list[dict] = []
    versions = set(manifest["configuration"]["versions"])
    for (block, scenario), metrics in sorted(pairs.items(), key=lambda item: (item[0][1], item[0][0])):
        for metric in METRIC_NAMES:
            missing_versions = sorted(versions - metrics[metric])
            if missing_versions:
                incomplete.append({
                    "block": block,
                    "scenario": scenario,
                    "metric": metric,
                    "missing_versions": missing_versions,
                })

    report = {
        "campaign_id": manifest["campaign_id"],
        "raw_directory": str(campaign_dir.relative_to(LAB_ROOT)).replace("\\", "/") if campaign_dir.is_relative_to(LAB_ROOT) else str(campaign_dir),
        "dataset": dataset_path.name,
        "counts": {
            "planned_rounds": len(manifest["planned_rounds"]),
            "validated_rounds": len(rows),
            "excluded_rounds": len(failures),
            "accepted_blocks": len({row["block"] for row in rows}),
        },
        "missing_by_metric": missing_by_metric,
        "failures": failures,
        "incomplete_pairs": incomplete,
        "raw_preserved": True,
        "imputation": "none",
    }
    quality_path = output_dir / f"{manifest['campaign_id']}_quality.json"
    quality_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

    markdown = [
        f"# Relatório de qualidade — {manifest['campaign_id']}", "",
        "## Resumo", "",
        f"- Rodadas planejadas: **{report['counts']['planned_rounds']}**",
        f"- Rodadas validadas: **{report['counts']['validated_rounds']}**",
        f"- Rodadas excluídas: **{report['counts']['excluded_rounds']}**",
        f"- Blocos validados: **{report['counts']['accepted_blocks']}**",
        f"- Dataset: `{dataset_path.name}`",
        f"- Brutos preservados: **{report['raw_preserved']}**",
        "- Imputação: **nenhuma**", "",
        "## Ausentes por métrica", "",
        "| Métrica | Ausentes no dataset |", "|---|---:|",
    ]
    markdown.extend(f"| `{metric}` | {count} |" for metric, count in missing_by_metric.items())
    markdown.extend(["", "## Exclusões e falhas", ""])
    if failures:
        markdown.extend(["| Arquivo | Classificação | Motivo |", "|---|---|---|"])
        markdown.extend(f"| `{failure['source']}` | {failure['classification']} | {failure['reason']} |" for failure in failures)
    else:
        markdown.append("Nenhuma exclusão ou falha registrada.")
    markdown.extend(["", "## Pares incompletos", ""])
    if incomplete:
        markdown.extend(["| Bloco | Cenário | Métrica | Versões faltantes |", "|---|---|---|---|"])
        markdown.extend(
            f"| {item['block']} | {item['scenario']} | `{item['metric']}` | {', '.join(item['missing_versions'])} |"
            for item in incomplete
        )
    else:
        markdown.append("Nenhum par incompleto registrado.")

    markdown_path = output_dir / f"{manifest['campaign_id']}_quality.md"
    markdown_path.write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--output-dir", type=Path, default=LAB_ROOT / "data" / "processed")
    args = parser.parse_args()
    report = write_processed_dataset(args.campaign, args.output_dir)
    print(json.dumps(report["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
