from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab02.metrics_cli import main
from lab02.static_metrics import (
    STATUS_EMPTY,
    STATUS_INVALID,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_PARTIAL,
    StaticMetricsError,
    analyze_trial_source,
    default_output_path,
    load_config,
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


def test_invalid_configuration_is_reported_without_traceback(tmp_path: Path, capsys) -> None:
    config = tmp_path / "invalid.toml"
    config.write_text('[duplication]\nmin_block_lines = "quatro"\n', encoding="utf-8")
    output = tmp_path / "metrics.json"

    code = main(
        [
            "--trial-id",
            "P01-K01-AI",
            "--source",
            str(FIXTURES / "valid"),
            "--config",
            str(config),
            "--output",
            str(output),
        ]
    )

    assert code == 1
    assert "min_block_lines" in capsys.readouterr().out
    assert not output.exists()


def test_mixed_valid_and_invalid_sources_are_partial(tmp_path: Path) -> None:
    (tmp_path / "valid.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    result = analyze_trial_source(trial_id="P01-K06-AI", source=tmp_path)

    assert result.status == STATUS_PARTIAL
    assert result.loc is not None
    assert any("foram excluídos" in message for message in result.messages)


def test_module_without_functions_has_null_complexity(tmp_path: Path) -> None:
    source = tmp_path / "constants.py"
    source.write_text("ANSWER = 42\n", encoding="utf-8")

    result = analyze_trial_source(trial_id="P01-K06-MANUAL", source=source)

    assert result.status == STATUS_OK
    assert result.loc == 1
    assert result.cyclomatic_complexity_mean is None
    assert result.cyclomatic_complexity_max is None


def test_rejects_unsafe_trial_id_and_unsupported_loc_field(tmp_path: Path) -> None:
    with pytest.raises(StaticMetricsError, match="trial_id"):
        default_output_path("../outside", tmp_path)

    config = tmp_path / "invalid-field.toml"
    config.write_text('[radon]\nloc_field = "comments"\n', encoding="utf-8")
    with pytest.raises(StaticMetricsError, match="loc_field"):
        load_config(config)

    with pytest.raises(StaticMetricsError, match="inexistente"):
        load_config(tmp_path / "missing.toml")


def test_cli_rejects_unsafe_trial_id_without_traceback(capsys) -> None:
    code = main(["--trial-id", "../outside", "--source", str(FIXTURES / "valid")])

    assert code == 1
    assert "trial_id" in capsys.readouterr().out
