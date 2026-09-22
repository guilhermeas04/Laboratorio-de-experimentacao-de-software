from __future__ import annotations

from lab02.rq3_analysis import (
    DEFAULT_DESIGN,
    DEFAULT_METRICS_DIR,
    DEFAULT_RAW_DIR,
    assert_metrics_completeness,
    consolidate_metrics,
    main,
)


def test_all_eighteen_official_trials_have_valid_metrics() -> None:
    rows = consolidate_metrics(DEFAULT_DESIGN, DEFAULT_METRICS_DIR, DEFAULT_RAW_DIR)

    assert_metrics_completeness(rows)
    assert len(rows) == 18
    assert all(row.metrics_status == "ok" for row in rows)
    assert all(row.loc is not None for row in rows)
    assert all(row.cyclomatic_complexity_mean is not None for row in rows)
    assert all(row.cyclomatic_complexity_max is not None for row in rows)
    assert all(row.duplication_percentage is not None for row in rows)
    assert all(row.maintainability_index is not None for row in rows)


def test_check_completeness_cli_exits_zero() -> None:
    assert main(["--check-completeness"]) == 0
