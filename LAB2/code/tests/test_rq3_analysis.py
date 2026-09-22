from __future__ import annotations

import csv
import json
from pathlib import Path

from lab02.rq3_analysis import (
    DEFAULT_DESIGN,
    DEFAULT_METRICS_DIR,
    DEFAULT_RAW_DIR,
    analyze,
    completeness_report,
    consolidate_metrics,
    holm_correction,
    main,
)


def test_consolidation_covers_all_official_trials() -> None:
    rows = consolidate_metrics(DEFAULT_DESIGN, DEFAULT_METRICS_DIR, DEFAULT_RAW_DIR)

    assert len(rows) == 18
    assert {row.treatment for row in rows} == {"with_ai", "manual"}
    assert all(row.metrics_status == "ok" for row in rows)
    assert all(row.loc is not None for row in rows)
    assert all(row.cyclomatic_complexity_mean is not None for row in rows)


def test_completeness_and_analysis_payload() -> None:
    rows = consolidate_metrics(DEFAULT_DESIGN, DEFAULT_METRICS_DIR, DEFAULT_RAW_DIR)
    completeness = completeness_report(rows)
    payload = analyze(rows)

    assert completeness["official_trial_count"] == 18
    assert completeness["all_complete"] is True
    assert payload["trial_count"] == 18
    assert payload["descriptive"]["with_ai"]["loc"]["n"] == 9
    assert payload["descriptive"]["manual"]["loc"]["n"] == 9
    assert set(payload["wilcoxon"]) == {
        "loc",
        "cyclomatic_complexity_mean",
        "cyclomatic_complexity_max",
        "duplication_percentage",
        "maintainability_index",
    }
    assert "holm" in payload
    assert payload["extremes"]["loc"]["max"] is not None


def test_holm_correction_orders_thresholds() -> None:
    adjusted = holm_correction(
        {
            "a": 0.01,
            "b": 0.04,
            "c": 0.20,
            "d": None,
        },
        alpha=0.05,
    )

    assert adjusted["a"]["holm_threshold"] == round(0.05 / 3, 6)
    assert adjusted["b"]["holm_threshold"] == round(0.05 / 2, 6)
    assert adjusted["c"]["holm_threshold"] == round(0.05 / 1, 6)
    assert adjusted["d"]["reject_h0"] is False


def test_cli_writes_rq3_artifacts(tmp_path: Path) -> None:
    assert main(["--reports-dir", str(tmp_path)]) == 0

    csv_path = tmp_path / "rq3-trials.csv"
    json_path = tmp_path / "rq3-statistics.json"
    markdown_path = tmp_path / "rq3-summary.md"

    assert csv_path.exists()
    assert json_path.exists()
    assert markdown_path.exists()

    with csv_path.open(newline="", encoding="utf-8") as file:
        assert len(list(csv.DictReader(file))) == 18

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["trial_count"] == 18
    assert payload["completeness"]["all_complete"] is True
    text = markdown_path.read_text(encoding="utf-8")
    assert "RQ3" in text
    assert "LOC" in text
