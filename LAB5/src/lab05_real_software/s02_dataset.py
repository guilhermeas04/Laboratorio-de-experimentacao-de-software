"""Validate and transform the complete LAB05S02 PostgreSQL campaign."""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path, PurePosixPath
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
    planned_positions = {
        (item["block"], item["scenario"], item["software_version"]): item["position"]
        for item in planned
    }
    if len(planned_positions) != len(planned):
        raise CampaignValidationError("duplicate planned block/scenario/version")

    rows: list[dict] = []
    failures: list[dict] = []
    seen_keys: set[tuple] = set()
    tracked: set[str] = set()
    recorded_statuses: list[str] = []
    accepted_blocks: set[int] = set()
    accepted_rounds = 0
    if (directory / "rounds").is_symlink():
        raise CampaignValidationError("rounds/ must be a directory inside the campaign")

    for attempt in manifest["attempts"]:
        accepted = attempt["status"] == "accepted"
        if accepted:
            if attempt["block"] in accepted_blocks:
                raise CampaignValidationError("multiple accepted attempts for the same block")
            accepted_blocks.add(attempt["block"])
        elif not attempt["records"]:
            failures.append({"source": attempt["execution_id"], "classification": "attempt",
                             "reason": attempt.get("deviation") or f"attempt {attempt['status']} without raw records"})
        for entry in attempt["records"]:
            relative = entry["file"]
            path = directory / relative
            if (PurePosixPath(relative).as_posix() != relative
                    or Path(relative).parts != ("rounds", path.name)
                    or path.suffix != ".json" or path.is_symlink()):
                raise CampaignValidationError("manifest record must be a JSON file directly under rounds/")
            if relative in tracked:
                failures.append({"source": relative, "reason": "duplicate raw reference in manifest",
                                 "classification": "manifest"})
                continue
            tracked.add(relative)
            if not path.is_file():
                failures.append({"source": relative, "reason": "missing raw record", "classification": "missing"})
                continue
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append({"source": relative, "reason": f"invalid JSON: {exc.msg}", "classification": "invalid"})
                continue

            if not isinstance(record, dict):
                failures.append({"source": relative, "reason": "raw record must be a JSON object", "classification": "invalid"})
                continue
            reasons: list[str] = []
            status = record.get("status")
            configured_version = record.get("software_version")
            images = manifest["environment"].get("images", {})
            image_matches = (isinstance(configured_version, str) and configured_version in images
                             and record.get("image_id") == images[configured_version])
            # The collector records image drift as a manifest failure even if the query ran.
            reconciled_status = "error" if status == "success" and not image_matches else status
            recorded_statuses.append(reconciled_status if reconciled_status in ("success", "error") else "invalid")
            if reconciled_status not in ("success", "error") or reconciled_status != entry.get("status"):
                failures.append({"source": relative, "reason": "raw status differs from manifest or is invalid",
                                 "classification": "manifest"})
                reasons.append("invalid manifest status")
            if not accepted:
                failures.append({
                    "source": relative, "classification": "attempt",
                    "reason": record.get("error") or record.get("cleanup_error") or entry.get("reason")
                    or attempt.get("deviation") or f"round from {attempt['status']} attempt",
                })
                continue
            if reconciled_status == entry.get("status") == "success":
                accepted_rounds += 1
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

            block, scenario, version = (record.get(field) for field in ("block", "scenario", "software_version"))
            key = (block, scenario, version)
            valid_key = type(block) is int and isinstance(scenario, str) and isinstance(version, str)
            if not valid_key or key not in planned_positions or block != attempt["block"]:
                reasons.append("record does not belong to the planned campaign")
            elif type(record.get("position")) is not int or record["position"] != planned_positions[key]:
                reasons.append("position differs from the planned order")

            if valid_key and key in seen_keys:
                reasons.append("duplicate block/scenario/version record")

            try:
                collected = _timestamp(record.get("collected_at"), "collected_at")
                ended = _timestamp(record["ended_at"], "ended_at")
                if ended < collected:
                    reasons.append("ended_at precedes collected_at")
            except (KeyError, CampaignValidationError) as exc:
                reasons.append(str(exc))

            server_version = record.get("server_version")
            if not isinstance(server_version, str) or not isinstance(configured_version, str):
                reasons.append("server_version or software_version has invalid type")
            elif server_version.split()[:1] != [configured_version]:
                reasons.append("server version differs from configured version")

            if record.get("round_id") != path.stem:
                reasons.append("round_id differs from raw filename")
            if not image_matches:
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
            seen_keys.add(key)

    actual = {path.relative_to(directory).as_posix() for path in (directory / "rounds").glob("*.json")}
    for relative in sorted(actual - tracked):
        failures.append({"source": relative, "reason": "raw file is not tracked in the manifest",
                         "classification": "manifest"})
    # A complete campaign has an accepted attempt for every planned block and slot.
    expected = {
        "planned": len(planned), "recorded": len(tracked & actual),
        "successful": recorded_statuses.count("success"), "failed": recorded_statuses.count("error"),
        "accepted_blocks": len(accepted_blocks), "accepted_rounds": accepted_rounds,
        "pending_rounds": len(planned) - accepted_rounds,
    }
    counts = manifest.get("counts", {})
    if not isinstance(counts, dict):
        raise CampaignValidationError("counts must be a JSON object")
    for field, value in expected.items():
        if type(counts.get(field)) is not int or counts[field] != value:
            failures.append({"source": "manifest.json", "reason": f"counts.{field} differs from reconciled value {value}",
                             "classification": "manifest"})
    if expected["pending_rounds"]:
        failures.append({"source": "manifest.json", "reason": "complete campaign has pending rounds",
                         "classification": "manifest"})
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

    planned = manifest["planned_rounds"]
    missing_by_metric = {metric: len(planned) - sum(row[metric] is not None for row in rows) for metric in METRIC_NAMES}
    # Pairs require both versions for the same block and scenario, per metric.
    pairs = {(item["block"], item["scenario"]): {metric: set() for metric in METRIC_NAMES} for item in planned}
    for row in rows:
        pair = pairs[(row["block"], row["scenario"])]
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
        "raw_directory": campaign_dir.as_posix(),
        "dataset": dataset_path.name,
        "counts": {
            "planned_rounds": len(manifest["planned_rounds"]),
            "validated_rounds": len(rows),
            "excluded_rounds": len(planned) - len(rows),
            "accepted_blocks": len({item["block"] for item in planned} - {item["block"] for item in incomplete}),
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
        "| Métrica | Rodadas planejadas sem valor validado |", "|---|---:|",
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
    return int(any(item["classification"] == "manifest" for item in report["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
