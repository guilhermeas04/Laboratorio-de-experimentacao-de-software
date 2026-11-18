"""Export the measured PostgreSQL pilot metrics from validated raw JSON."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from .analysis import DEFAULT_METRICS, ROOT, PilotAnalysisError
from .validator import validate_raw_directory


def export_pilot_metrics(raw_dir: Path, output: Path) -> Path:
    rows = []
    for record in validate_raw_directory(raw_dir):
        version = record["software_version"]
        if record["software"] != "PostgreSQL" or not version.split(".")[0].isdigit():
            continue

        latency = None
        if record["status"] == "success":
            try:
                server_version, plan = record["stdout"].split("\n", 1)
                if server_version.split()[0] != version:
                    raise ValueError("server version differs from the recorded version")
                latency = json.loads(plan)[0]["Execution Time"]
                if type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0:
                    raise ValueError("invalid Execution Time")
            except (IndexError, KeyError, TypeError, ValueError) as exc:
                raise PilotAnalysisError(f"Plano PostgreSQL inválido em {record['identifier']}") from exc

        rows.append({
            "software_version": version,
            "block": record["repetition"],
            "query_latency_ms": latency,
            "throughput_queries_per_second": None,
            "cpu_percent": None,
            "memory_mb": None,
            "duration_ms": record.get("duration_ms"),
            "source": record["identifier"] + ".json",
        })
    if not rows:
        raise PilotAnalysisError("nenhum registro de coleta PostgreSQL encontrado")
    rows.sort(key=lambda row: (row["block"], row["software_version"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--output", type=Path, default=DEFAULT_METRICS)
    args = parser.parse_args()
    print(export_pilot_metrics(args.raw_dir, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
