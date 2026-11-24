"""Reproducible validity diagnostics for the complete LAB05S02 campaign."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .s02_descriptive import DEFAULT_DATASET, ROOT, load_validated_dataset


DEFAULT_CAMPAIGN = ROOT / "data" / "raw" / "s02" / "lab05s02-20261121-01"
DEFAULT_OUTPUT = ROOT / "reports" / "validity"
LOWER_IS_BETTER = {"query_latency_ms", "cpu_percent", "memory_mb", "client_latency_ms"}
METRICS = (
    "query_latency_ms",
    "throughput_queries_per_second",
    "cpu_percent",
    "memory_mb",
    "client_latency_ms",
    "resource_window_seconds",
)


class ValidityDiagnosticError(ValueError):
    """Raised when campaign artifacts cannot support validity diagnostics."""


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidityDiagnosticError(f"cannot read JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise ValidityDiagnosticError(f"JSON artifact must contain an object: {path}")
    return value


def _artifact_label(path: Path) -> str:
    resolved = path.resolve()
    repository = ROOT.parent
    return resolved.relative_to(repository).as_posix() if resolved.is_relative_to(repository) else str(path)


def _paired_rows(frame: pd.DataFrame, scenario: str, metric: str, versions: list[str]) -> pd.DataFrame:
    selected = frame.loc[frame["scenario"].astype(str) == scenario]
    left = selected.loc[selected["software_version"].astype(str) == versions[0], ["block", "position", metric]]
    right = selected.loc[selected["software_version"].astype(str) == versions[1], ["block", "position", metric]]
    left = left.rename(columns={"position": "position_a", metric: "value_a"})
    right = right.rename(columns={"position": "position_b", metric: "value_b"})
    paired = left.merge(right, on="block", how="inner", validate="one_to_one")
    paired = paired.dropna(subset=["value_a", "value_b"]).copy()
    paired["difference_a_minus_b"] = paired["value_a"] - paired["value_b"]
    paired["order"] = np.where(
        paired["position_a"] < paired["position_b"],
        f"{versions[0]}_first",
        f"{versions[1]}_first",
    )
    return paired


def _improvement_percent(value_a: float, value_b: float, metric: str) -> float | None:
    if metric == "resource_window_seconds" or value_a == 0:
        return None
    numerator = value_a - value_b if metric in LOWER_IS_BETTER else value_b - value_a
    return 100 * numerator / value_a


def _summary(pairs: pd.DataFrame, metric: str) -> dict[str, Any]:
    if pairs.empty:
        return {
            "n_pairs": 0,
            "mean_difference_a_minus_b": None,
            "median_difference_a_minus_b": None,
            "mean_improvement_percent": None,
            "median_improvement_percent": None,
            "min_improvement_percent": None,
            "max_improvement_percent": None,
        }
    a = pairs["value_a"].to_numpy(dtype=float)
    b = pairs["value_b"].to_numpy(dtype=float)
    differences = a - b
    pairwise_improvements = [
        value for left, right in zip(a, b, strict=True)
        if (value := _improvement_percent(float(left), float(right), metric)) is not None
    ]
    return {
        "n_pairs": int(len(pairs)),
        "mean_difference_a_minus_b": float(np.mean(differences)),
        "median_difference_a_minus_b": float(np.median(differences)),
        "mean_improvement_percent": _improvement_percent(float(np.mean(a)), float(np.mean(b)), metric),
        "median_improvement_percent": float(np.median(pairwise_improvements)) if pairwise_improvements else None,
        "min_improvement_percent": float(min(pairwise_improvements)) if pairwise_improvements else None,
        "max_improvement_percent": float(max(pairwise_improvements)) if pairwise_improvements else None,
    }


def _check_raw_consistency(campaign_dir: Path, manifest: dict) -> dict:
    expected_configuration = manifest["configuration"]
    expected_images = manifest.get("environment", {}).get("images", {})
    checked = 0
    issues: list[dict[str, str]] = []
    common_environment: dict | None = None
    for attempt in manifest.get("attempts", []):
        for entry in attempt.get("records", []):
            relative = entry.get("file", "")
            path = campaign_dir / relative
            if not path.is_file():
                issues.append({"source": relative, "issue": "raw record missing"})
                continue
            record = _read_json(path)
            checked += 1
            if record.get("configuration") != expected_configuration:
                issues.append({"source": relative, "issue": "configuration differs from campaign manifest"})
            version = str(record.get("software_version", ""))
            if record.get("image_id") != expected_images.get(version):
                issues.append({"source": relative, "issue": "image_id differs from version in campaign manifest"})
            environment = record.get("environment", {})
            if common_environment is None:
                common_environment = environment
            elif environment != common_environment:
                issues.append({"source": relative, "issue": "round environment differs from other versions/rounds"})
    return {
        "records_checked": checked,
        "consistent": not issues,
        "issues": issues,
        "campaign_configuration": expected_configuration,
        "image_ids_by_version": expected_images,
    }


def diagnose_validity(
    *,
    dataset_path: Path = DEFAULT_DATASET,
    campaign_dir: Path = DEFAULT_CAMPAIGN,
    quality_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict[str, Path]:
    """Generate configuration, order, block-stability, and exclusion diagnostics."""
    dataset_path = Path(dataset_path)
    campaign_dir = Path(campaign_dir)
    output_dir = Path(output_dir)
    frame = load_validated_dataset(dataset_path)
    manifest = _read_json(campaign_dir / "manifest.json")
    if manifest.get("campaign_id") != str(frame["campaign_id"].iloc[0]):
        raise ValidityDiagnosticError("campaign ID does not match the validated dataset")
    configuration = manifest.get("configuration", {})
    versions = configuration.get("versions", [])
    if len(versions) != 2 or not all(isinstance(version, str) for version in versions):
        raise ValidityDiagnosticError("campaign must configure exactly two version labels")

    if quality_path is None:
        quality_path = dataset_path.parent / f"{manifest['campaign_id']}_quality.json"
    quality_path = Path(quality_path)
    quality = _read_json(quality_path) if quality_path.is_file() else {}

    consistency = _check_raw_consistency(campaign_dir, manifest)
    primary = configuration.get("primary", {})
    primary_scenario = primary.get("scenario", "customer_total")
    primary_metric = primary.get("metric", "query_latency_ms")
    practical_threshold = float(primary.get("minimum_relative_reduction", 0.1)) * 100

    rows: list[dict[str, Any]] = []
    sensitivity: list[dict[str, Any]] = []
    scenarios = sorted(str(value) for value in frame["scenario"].dropna().unique())
    metric_names = [metric for metric in METRICS if metric in frame.columns]
    for scenario in scenarios:
        for metric in metric_names:
            pairs = _paired_rows(frame, scenario, metric, versions)
            full = _summary(pairs, metric)
            is_primary = scenario == primary_scenario and metric == primary_metric
            practical_label = (
                "threshold_met" if full["mean_improvement_percent"] is not None
                and full["mean_improvement_percent"] >= practical_threshold else "threshold_not_met"
            ) if is_primary else None
            rows.append({
                "scenario": scenario,
                "metric": metric,
                "diagnostic": "mean_vs_median",
                "stratum": "all_complete_pairs",
                **full,
                "practical_threshold_percent": practical_threshold if is_primary else None,
                "practical_interpretation": practical_label,
            })

            if pairs.empty:
                continue
            for order, group in pairs.groupby("order", sort=True):
                result = _summary(group, metric)
                sensitivity.append({
                    "scenario": scenario,
                    "metric": metric,
                    "diagnostic": "order_sensitivity",
                    "stratum": order,
                    **result,
                    "practical_threshold_percent": practical_threshold if is_primary else None,
                    "practical_interpretation": (
                        "threshold_met" if is_primary and result["mean_improvement_percent"] is not None
                        and result["mean_improvement_percent"] >= practical_threshold
                        else "threshold_not_met" if is_primary else None
                    ),
                })

            blocks = sorted(int(block) for block in pairs["block"].unique())
            midpoint = len(blocks) // 2
            for label, chosen in (("first_half_blocks", set(blocks[:midpoint])),
                                  ("second_half_blocks", set(blocks[midpoint:]))):
                result = _summary(pairs.loc[pairs["block"].astype(int).isin(chosen)], metric)
                sensitivity.append({
                    "scenario": scenario,
                    "metric": metric,
                    "diagnostic": "block_stability",
                    "stratum": label,
                    **result,
                    "practical_threshold_percent": practical_threshold if is_primary else None,
                    "practical_interpretation": (
                        "threshold_met" if is_primary and result["mean_improvement_percent"] is not None
                        and result["mean_improvement_percent"] >= practical_threshold
                        else "threshold_not_met" if is_primary else None
                    ),
                })

            if len(pairs) > 1:
                loo = [_summary(pairs.loc[pairs["block"] != block], metric) for block in blocks]
                values = [item["mean_improvement_percent"] for item in loo if item["mean_improvement_percent"] is not None]
                sensitivity.append({
                    "scenario": scenario,
                    "metric": metric,
                    "diagnostic": "leave_one_block_out",
                    "stratum": "range_across_omitted_blocks",
                    "n_pairs": len(pairs) - 1,
                    "mean_difference_a_minus_b": None,
                    "median_difference_a_minus_b": None,
                    "mean_improvement_percent": None,
                    "median_improvement_percent": None,
                    "min_improvement_percent": float(min(values)) if values else None,
                    "max_improvement_percent": float(max(values)) if values else None,
                    "practical_threshold_percent": practical_threshold if is_primary else None,
                    "practical_interpretation": "min/max improvement across omitted blocks" if is_primary else None,
                })

    attempts = manifest.get("attempts", [])
    unsuccessful_attempts = [attempt for attempt in attempts if attempt.get("status") != "accepted"]
    excluded_blocks = {int(attempt["block"]) for attempt in unsuccessful_attempts if "block" in attempt}
    failure_pairs = frame.loc[~frame["block"].astype(int).isin(excluded_blocks)]
    for scenario in scenarios:
        pairs = _paired_rows(frame, scenario, primary_metric, versions)
        retained = _paired_rows(failure_pairs, scenario, primary_metric, versions)
        for label, selection in (("all_validated_blocks", pairs), ("exclude_retry_or_failed_blocks", retained)):
            result = _summary(selection, primary_metric)
            sensitivity.append({
                "scenario": scenario,
                "metric": primary_metric,
                "diagnostic": "failure_exclusion_policy",
                "stratum": label,
                **result,
                "practical_threshold_percent": practical_threshold if scenario == primary_scenario else None,
                "practical_interpretation": (
                    "threshold_met" if scenario == primary_scenario and result["mean_improvement_percent"] is not None
                    and result["mean_improvement_percent"] >= practical_threshold
                    else "threshold_not_met" if scenario == primary_scenario else None
                ),
            })

    improvement_values = [
        row["mean_improvement_percent"] for row in sensitivity
        if row["scenario"] == primary_scenario and row["metric"] == primary_metric
        and row["diagnostic"] in {"order_sensitivity", "block_stability"}
        and row["mean_improvement_percent"] is not None
    ]
    primary_full = next((row for row in rows if row["scenario"] == primary_scenario and row["metric"] == primary_metric), {})
    full_interpretation = primary_full.get("practical_interpretation")
    median_interpretation = (
        "threshold_met" if primary_full.get("median_improvement_percent") is not None
        and primary_full["median_improvement_percent"] >= practical_threshold else "threshold_not_met"
    )
    alternative_interpretations = {
        row.get("practical_interpretation") for row in sensitivity
        if row["scenario"] == primary_scenario and row["metric"] == primary_metric
        and row["diagnostic"] in {"order_sensitivity", "block_stability", "failure_exclusion_policy"}
        and row.get("practical_interpretation")
    }
    alternative_interpretations.add(median_interpretation)
    interpretation_changes = bool(full_interpretation and any(value != full_interpretation for value in alternative_interpretations))

    summary = {
        "issue": 154,
        "campaign_id": manifest["campaign_id"],
        "dataset": _artifact_label(dataset_path),
        "campaign_manifest": _artifact_label(campaign_dir / "manifest.json"),
        "quality_report": _artifact_label(quality_path) if quality_path.is_file() else None,
        "design": {
            "versions": versions,
            "scenarios": scenarios,
            "blocks": int(frame["block"].nunique()),
            "primary_scenario": primary_scenario,
            "primary_metric": primary_metric,
            "minimum_relative_reduction_percent": practical_threshold,
        },
        "consistency": consistency,
        "collection": {
            "manifest_status": manifest.get("status"),
            "planned_rounds": manifest.get("counts", {}).get("planned"),
            "recorded_rounds": manifest.get("counts", {}).get("recorded"),
            "successful_rounds": manifest.get("counts", {}).get("successful"),
            "failed_rounds": manifest.get("counts", {}).get("failed"),
            "accepted_blocks": manifest.get("counts", {}).get("accepted_blocks"),
            "manifest_deviations": manifest.get("deviations", []),
            "nonaccepted_attempts": len(unsuccessful_attempts),
            "quality_exclusions": quality.get("failures", []),
            "incomplete_pairs": quality.get("incomplete_pairs", []),
        },
        "sensitivity": {
            "mean_vs_median": "The primary mean paired contrast is reported with the median paired contrast; the primary decision remains the preregistered mean.",
            "order": "Contrasts are stratified by which version ran first.",
            "block_stability": "Contrasts are compared across the first and second half of ordered block identifiers and by leave-one-block-out range.",
            "failures_and_exclusions": "Reports observed nonaccepted attempts and quality exclusions; compares the validated estimate with a strict exclusion of any block having a nonaccepted attempt.",
            "primary_interpretation_changes": interpretation_changes,
            "primary_full_data_interpretation": full_interpretation,
            "primary_median_sensitivity_interpretation": median_interpretation,
            "primary_alternative_interpretations": sorted(alternative_interpretations),
            "primary_order_block_improvement_range_percent": [min(improvement_values), max(improvement_values)] if improvement_values else None,
            "note": "These are descriptive sensitivity diagnostics, not additional confirmatory tests or a replacement for the preregistered primary analysis.",
        },
        "limitations": [
            "Inference is limited to the two tested PostgreSQL versions, two specified SQL queries, deterministic synthetic dataset, and measured local Docker host/configuration.",
            "No external production workload, concurrent user population, other hardware, operating systems, PostgreSQL versions, schemas, or query distributions were sampled.",
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{manifest['campaign_id']}_validity"
    json_path = output_dir / f"{prefix}.json"
    csv_path = output_dir / f"{prefix}.csv"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        fields = [
            "scenario", "metric", "diagnostic", "stratum", "n_pairs",
            "mean_difference_a_minus_b", "median_difference_a_minus_b",
            "mean_improvement_percent", "median_improvement_percent",
            "min_improvement_percent", "max_improvement_percent",
            "practical_threshold_percent", "practical_interpretation",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows + sensitivity)
    return {"summary": json_path, "diagnostics": csv_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN)
    parser.add_argument("--quality-report", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    paths = diagnose_validity(
        dataset_path=args.dataset,
        campaign_dir=args.campaign,
        quality_path=args.quality_report,
        output_dir=args.output_dir,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())