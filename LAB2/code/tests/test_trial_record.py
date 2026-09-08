from __future__ import annotations

import pytest

from lab02 import MAX_TRIAL_SECONDS, TrialRecord, TrialValidationError


def valid_payload() -> dict[str, object]:
    return {
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
        "loc": None,
        "cyclomatic_complexity_mean": None,
        "cyclomatic_complexity_max": None,
        "duplication_percentage": None,
        "maintainability_index": None,
    }


def test_accepts_complete_ai_trial() -> None:
    record = TrialRecord.from_mapping(valid_payload())

    assert record.trial_id == "P01-K01-AI"
    assert record.to_dict()["success_rate"] == 100.0


def test_accepts_censored_manual_trial() -> None:
    payload = valid_payload()
    payload.update(
        treatment="manual",
        elapsed_seconds=MAX_TRIAL_SECONDS,
        time_to_green_seconds=None,
        censored=True,
        tests_passing=9,
        success_rate=75.0,
        prompt_count=None,
        assistant_name=None,
        assistant_version=None,
    )

    record = TrialRecord.from_mapping(payload)

    assert record.censored is True
    assert record.elapsed_seconds == MAX_TRIAL_SECONDS


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"elapsed_seconds": 2101}, "elapsed_seconds"),
        ({"success_rate": 99.0}, "success_rate"),
        ({"tests_passing": 11}, "todos os testes"),
        ({"assistant_name": None}, "assistant_name"),
        ({"started_at": "2026-09-08T19:00:00"}, "fuso horário"),
        ({"cyclomatic_complexity_mean": 4.0, "cyclomatic_complexity_max": 3}, "complexidade média"),
        ({"tests_total": "12"}, "tests_total"),
        ({"tests_passing": "12"}, "tests_passing"),
        ({"elapsed_seconds": "750"}, "elapsed_seconds"),
        ({"cyclomatic_complexity_mean": "baixa", "cyclomatic_complexity_max": "alta"}, "número não negativo"),
    ],
)
def test_rejects_inconsistent_records(changes: dict[str, object], message: str) -> None:
    payload = valid_payload()
    payload.update(changes)

    with pytest.raises(TrialValidationError, match=message):
        TrialRecord.from_mapping(payload)


def test_rejects_censored_trial_with_success() -> None:
    payload = valid_payload()
    payload.update(
        elapsed_seconds=MAX_TRIAL_SECONDS,
        time_to_green_seconds=None,
        censored=True,
    )

    with pytest.raises(TrialValidationError, match="pelo menos um teste falhando"):
        TrialRecord.from_mapping(payload)


def test_rejects_unknown_and_missing_fields() -> None:
    payload = valid_payload()
    del payload["trial_id"]
    payload["unexpected"] = "value"

    with pytest.raises(TrialValidationError) as error:
        TrialRecord.from_mapping(payload)

    assert "campos desconhecidos: unexpected" in str(error.value)
    assert "campos obrigatórios ausentes: trial_id" in str(error.value)
