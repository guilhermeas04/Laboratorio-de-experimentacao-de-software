from __future__ import annotations

import json
from pathlib import Path

from lab02.metrics_cli import main
from lab02.static_metrics import (
    STATUS_EMPTY,
    STATUS_INVALID,
    STATUS_MISSING,
    STATUS_OK,
    analyze_trial_source,
)
from lab02.trial_record import TrialRecord

FIXTURES = Path(__file__).parent / "fixtures" / "metrics"


def test_analyzes_valid_source_with_radon_metrics() -> None:
    result = analyze_trial_source(trial_id="P01-K01-AI", source=FIXTURES / "valid")

    assert result.status == STATUS_OK
    assert result.loc is not None and result.loc > 0
    assert result.cyclomatic_complexity_mean is not None
    assert result.cyclomatic_complexity_max is not None
    assert result.cyclomatic_complexity_max >= result.cyclomatic_complexity_mean
    assert result.duplication_percentage is not None
    assert result.maintainability_index is not None
    assert 0 <= result.maintainability_index <= 100


def test_detects_duplication_above_zero() -> None:
    result = analyze_trial_source(trial_id="P01-K02-AI", source=FIXTURES / "duplicated")

    assert result.status == STATUS_OK
    assert result.duplication_percentage is not None
    assert result.duplication_percentage > 0


def test_empty_source_is_not_zero() -> None:
    result = analyze_trial_source(trial_id="P01-K03-MANUAL", source=FIXTURES / "empty_dir")

    assert result.status == STATUS_EMPTY
    assert result.loc is None
    assert result.cyclomatic_complexity_mean is None
    assert result.cyclomatic_complexity_max is None
    assert result.duplication_percentage is None
    assert result.maintainability_index is None


def test_empty_file_is_not_zero() -> None:
    result = analyze_trial_source(trial_id="P01-K03-AI", source=FIXTURES / "empty_file")

    assert result.status == STATUS_EMPTY
    assert result.loc is None
    assert result.maintainability_index is None


def test_invalid_code_is_not_zero() -> None:
    result = analyze_trial_source(trial_id="P01-K04-AI", source=FIXTURES / "invalid")

    assert result.status == STATUS_INVALID
    assert result.loc is None
    assert result.cyclomatic_complexity_mean is None
    assert result.duplication_percentage is None
    assert result.maintainability_index is None
    assert any("inválido" in message for message in result.messages)


def test_missing_source_is_explicit(tmp_path: Path) -> None:
    result = analyze_trial_source(trial_id="P01-K05-AI", source=tmp_path / "ausente")

    assert result.status == STATUS_MISSING
    assert result.loc is None


def test_metric_fields_integrate_with_trial_schema() -> None:
    result = analyze_trial_source(trial_id="P01-K01-AI", source=FIXTURES / "valid")
    payload = {
        "schema_version": "1.0",
        "trial_id": "P01-K01-AI",
        "participant": "participant-01",
        "kata_id": "kata-01",
        "treatment": "with_ai",
        "execution_order": 1,
        "started_at": "2026-09-08T19:00:00-03:00",
        "finished_at": "2026-09-08T19:12:30-03:00",
        "elapsed_seconds": 750.0,
        "time_to_green_seconds": 750.0,
        "censored": False,
        "tests_total": 12,
        "tests_passing": 12,
        "success_rate": 100.0,
        "prompt_count": 4,
        "assistant_name": "assistente-exemplo",
        "assistant_version": "versao-exemplo",
        **result.metric_fields(),
    }

    record = TrialRecord.from_mapping(payload)

    assert record.loc == result.loc
    assert record.maintainability_index == result.maintainability_index


def test_cli_writes_structured_output(tmp_path: Path, capsys) -> None:
    output = tmp_path / "metrics-P01-K01-AI.json"
    code = main(
        [
            "--trial-id",
            "P01-K01-AI",
            "--source",
            str(FIXTURES / "valid"),
            "--output",
            str(output),
        ]
    )

    assert code == 0
    assert "OK: trial=P01-K01-AI" in capsys.readouterr().out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["trial_id"] == "P01-K01-AI"
    assert payload["status"] == STATUS_OK
    assert payload["loc"] > 0


def test_cli_signals_analysis_problems(tmp_path: Path) -> None:
    output = tmp_path / "metrics-P01-K04-AI.json"
    code = main(
        [
            "--trial-id",
            "P01-K04-AI",
            "--source",
            str(FIXTURES / "invalid"),
            "--output",
            str(output),
        ]
    )

    assert code == 2
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == STATUS_INVALID
    assert payload["loc"] is None
