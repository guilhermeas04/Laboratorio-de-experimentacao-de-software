from __future__ import annotations

import csv
import json
from pathlib import Path

from lab02.rq12_analysis import (
    DEFAULT_DESIGN,
    DEFAULT_RAW_DIR,
    analyze,
    consolidate_trials,
    main,
    wilcoxon_signed_rank,
)


def test_consolidation_uses_only_official_trials() -> None:
    rows = consolidate_trials(DEFAULT_DESIGN, DEFAULT_RAW_DIR)

    assert len(rows) == 18
    assert "P01-K01-MANUAL" not in {row.trial_id for row in rows}
    assert {row.treatment for row in rows} == {"with_ai", "manual"}
    assert all(row.tests_failing == row.tests_total - row.tests_passing for row in rows)


def test_analysis_contains_descriptive_stats_and_wilcoxon_results() -> None:
    payload = analyze(consolidate_trials(DEFAULT_DESIGN, DEFAULT_RAW_DIR))

    assert payload["trial_count"] == 18
    assert payload["descriptive"]["with_ai"]["elapsed_seconds"]["n"] == 9
    assert payload["descriptive"]["manual"]["elapsed_seconds"]["n"] == 9
    assert payload["wilcoxon"]["rq1_elapsed_seconds"]["status"] == "ok"
    assert "rq2_tests_failing" in payload["wilcoxon"]


def test_wilcoxon_exact_less_and_zero_differences() -> None:
    result = wilcoxon_signed_rank((-3.0, -2.0, -1.0), alternative="less")

    assert result.status == "ok"
    assert result.n_pairs == 3
    assert result.statistic_w_plus == 0
    assert result.p_value_exact == 0.125

    tied = wilcoxon_signed_rank((0.0, 0.0, 0.0), alternative="less")
    assert tied.status == "not_applicable"
    assert tied.p_value_exact is None


def test_cli_writes_reproducible_report_files(tmp_path: Path) -> None:
    assert main(["--reports-dir", str(tmp_path)]) == 0

    csv_path = tmp_path / "rq12-trials.csv"
    json_path = tmp_path / "rq12-statistics.json"
    markdown_path = tmp_path / "rq12-summary.md"

    assert csv_path.exists()
    assert json_path.exists()
    assert markdown_path.exists()

    with csv_path.open(newline="", encoding="utf-8") as file:
        assert len(list(csv.DictReader(file))) == 18

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["trial_count"] == 18
    assert "RQ1" in markdown_path.read_text(encoding="utf-8")
