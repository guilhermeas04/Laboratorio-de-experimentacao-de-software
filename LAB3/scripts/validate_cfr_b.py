"""Executa a validação offline da heurística CFR(b) contra a amostra-ouro."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, time
from pathlib import Path

from lab03_dora.metrics.cfr import calculate_cfr_b
from lab03_dora.validation.labels import validate_gold_standard


ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "data/raw/github/releases"
COMMITS = ROOT / "data/raw/github/commits"
GOLD = ROOT / "data/processed/gold_standard/gold_standard_consensus.csv"
PREDICTIONS = ROOT / "data/processed/metrics/cfr_b_predictions.csv"
VALIDATION = ROOT / "reports/validation/cfr_b_validation.json"


def read_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    observation_end = datetime.combine(datetime(2025, 12, 31).date(), time.max, tzinfo=UTC)
    outcomes: list[dict] = []
    for releases_path in sorted(RELEASES.glob("*.json")):
        slug = releases_path.stem
        releases = read_json(releases_path)
        compares = read_json(COMMITS / releases_path.name)
        if not releases:
            continue
        summary = calculate_cfr_b(releases, compares, observation_end=observation_end)
        outcomes.extend(item.to_dict() for item in summary.outcomes)

    write_csv(PREDICTIONS, outcomes)
    validation = validate_gold_standard(read_csv(GOLD), outcomes)
    VALIDATION.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION.write_text(json.dumps(validation, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=False))
    print(f"predictions={PREDICTIONS}")
    print(f"validation={VALIDATION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
