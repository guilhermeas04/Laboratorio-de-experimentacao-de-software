"""Ponto de entrada reprodutível para as análises da Sprint 3."""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def run(command: list[str], root: Path) -> dict[str, object]:
    completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
    return {"command": command, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa as análises disponíveis da LAB3S03.")
    parser.add_argument("--input", type=Path, default=Path("data/processed/datasets/s02_metrics.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/sprint3"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    input_path = (root / args.input).resolve()
    with input_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < 300 or len({row.get("repository") for row in rows}) != len(rows):
        raise SystemExit("Entrada inválida: o dataset precisa ter pelo menos 300 repositórios únicos.")
    output = root / args.output
    output.mkdir(parents=True, exist_ok=True)
    commands = [
        [sys.executable, "-m", "lab03_dora.analysis.rq01_rq02", "--input", str(input_path)],
        [sys.executable, "-m", "lab03_dora.analysis.rq03_rq04", "--input", str(input_path)],
        [sys.executable, "-m", "lab03_dora.analysis.rq05", "--input", str(input_path)],
        [sys.executable, "-m", "lab03_dora.analysis.rq06"],
        [sys.executable, "scripts/rq07_sensitivity.py", "--input", str(input_path)],
    ]
    results = [run(command, root) for command in commands]
    manifest = {"generated_at_utc": datetime.now(UTC).isoformat(), "input": str(args.input), "repository_count": len(rows), "unique_repository_count": len({row.get("repository") for row in rows}), "analyses": results}
    (output / "sprint3_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed = [item for item in results if item["returncode"] != 0]
    print(f"Sprint 3: {len(rows)} repositorios; {len(results) - len(failed)}/{len(results)} análises concluídas.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
