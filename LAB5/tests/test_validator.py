import copy
import json
from pathlib import Path

import pytest

from lab05_real_software.validator import (
    RawDataValidationError,
    validate_pilot_record,
    validate_raw_directory,
    validate_raw_file,
)


ROOT = Path(__file__).parents[1]
RAW_DIR = ROOT / "data" / "raw"
VALID_RECORD = {
    "schema_version": "lab05-pilot-v1",
    "collected_at": "2026-11-18T12:17:33.669+00:00",
    "ended_at": "2026-11-18T12:17:33.828+00:00",
    "status": "success",
    "error": None,
    "software": "PostgreSQL",
    "software_version": "15",
    "repetition": 1,
    "command": ["python", "-c", "print('ok')"],
    "returncode": 0,
    "duration_ms": 159.0,
    "stdout": "ok\n",
    "stderr": "",
    "metadata": {
        "hostname": "lab-machine",
        "platform": "Windows-11",
        "python_version": "3.12.3",
        "execution_mode": "local",
        "timeout_seconds": 30.0,
    },
}


def test_valid_record_preserves_provenance(tmp_path):
    source = tmp_path / "pilot-15-r001.json"

    validated = validate_pilot_record(copy.deepcopy(VALID_RECORD), source_path=source)

    assert validated["identifier"] == "pilot-15-r001"
    assert validated["source"] == "local"
    assert validated["software"] == "PostgreSQL"
    assert validated["software_version"] == "15"
    assert validated["collected_at"] == VALID_RECORD["collected_at"]
    assert validated["configuration"]["execution_mode"] == "local"


@pytest.mark.parametrize("status", ["unknown", []])
def test_invalid_status_is_rejected(status):
    record = copy.deepcopy(VALID_RECORD)
    record["status"] = status

    with pytest.raises(RawDataValidationError, match="status"):
        validate_pilot_record(record)


@pytest.mark.parametrize("duration", [-1, "bad", True, float("nan"), float("inf")])
def test_invalid_duration_is_rejected(duration):
    record = copy.deepcopy(VALID_RECORD)
    record["duration_ms"] = duration

    with pytest.raises(RawDataValidationError, match="duration_ms"):
        validate_pilot_record(record)


@pytest.mark.parametrize("value", [None, "", 42])
def test_invalid_platform_is_rejected(value):
    record = copy.deepcopy(VALID_RECORD)
    record["metadata"]["platform"] = value

    with pytest.raises(RawDataValidationError, match="metadata.platform"):
        validate_pilot_record(record)


def test_missing_required_field_is_rejected():
    record = copy.deepcopy(VALID_RECORD)
    del record["software_version"]

    with pytest.raises(RawDataValidationError, match="software_version"):
        validate_pilot_record(record)


def test_timestamp_without_timezone_is_rejected():
    record = copy.deepcopy(VALID_RECORD)
    record["collected_at"] = "2026-11-18T12:17:33"

    with pytest.raises(RawDataValidationError, match="timezone"):
        validate_pilot_record(record)


def test_ended_at_before_collected_at_is_rejected():
    record = copy.deepcopy(VALID_RECORD)
    record["ended_at"] = "2026-11-18T12:17:32+00:00"

    with pytest.raises(RawDataValidationError, match="earlier"):
        validate_pilot_record(record)


def test_error_record_requires_message():
    record = copy.deepcopy(VALID_RECORD)
    record["status"] = "error"
    record["returncode"] = 1
    record["error"] = ""

    with pytest.raises(RawDataValidationError, match="non-empty error"):
        validate_pilot_record(record)


def test_invalid_success_returncode_is_rejected():
    record = copy.deepcopy(VALID_RECORD)
    record["returncode"] = 1

    with pytest.raises(RawDataValidationError, match="returncode 0"):
        validate_pilot_record(record)


def test_invalid_json_file_is_rejected(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(RawDataValidationError, match="Invalid JSON"):
        validate_raw_file(path)


def test_existing_pilot_records_are_validated_without_modification():
    before = {
        path.name: path.read_bytes()
        for path in RAW_DIR.glob("*.json")
    }

    records = validate_raw_directory(RAW_DIR)

    after = {
        path.name: path.read_bytes()
        for path in RAW_DIR.glob("*.json")
    }
    assert records
    assert before == after
    assert all(record["identifier"] for record in records)
    assert all(record["collected_at"] for record in records)
    assert all(record["software_version"] for record in records)
    assert all(record["configuration"] for record in records)
