"""Validation utilities for immutable LAB05 pilot records."""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


class RawDataValidationError(ValueError):
    """Raised when a raw pilot record violates the LAB05 data contract."""


REQUIRED_FIELDS = {
    "schema_version",
    "collected_at",
    "status",
    "software",
    "software_version",
    "repetition",
    "command",
    "metadata",
}
VALID_STATUSES = {"success", "error"}


def _require(mapping: dict[str, Any], field: str, context: str) -> Any:
    if field not in mapping:
        raise RawDataValidationError(f"Missing {context}.{field}")
    if mapping[field] is None:
        raise RawDataValidationError(f"{context}.{field} cannot be null")
    return mapping[field]


def _parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise RawDataValidationError(f"{field} must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RawDataValidationError(f"Invalid ISO-8601 timestamp in {field}: {value}") from exc
    if parsed.tzinfo is None:
        raise RawDataValidationError(f"{field} must include a timezone")
    return parsed


def validate_pilot_record(record: object, *, source_path: str | Path | None = None) -> dict[str, Any]:
    """Validate a raw record and return its original data plus provenance details."""
    if not isinstance(record, dict):
        raise RawDataValidationError("Raw record root must be a JSON object")

    missing = sorted(REQUIRED_FIELDS - record.keys())
    if missing:
        raise RawDataValidationError(f"Missing required fields: {', '.join(missing)}")

    if not isinstance(record["schema_version"], str) or not record["schema_version"]:
        raise RawDataValidationError("schema_version must be a non-empty string")
    if record["schema_version"] != "lab05-pilot-v1":
        raise RawDataValidationError(
            f"Unsupported schema_version: {record['schema_version']}"
        )

    collected_at = _parse_timestamp(record["collected_at"], "collected_at")
    if "ended_at" in record:
        ended_at = _parse_timestamp(record["ended_at"], "ended_at")
        if ended_at < collected_at:
            raise RawDataValidationError("ended_at cannot be earlier than collected_at")

    status = _require(record, "status", "record")
    if not isinstance(status, str) or status not in VALID_STATUSES:
        raise RawDataValidationError("status must be 'success' or 'error'")

    software = _require(record, "software", "record")
    software_version = _require(record, "software_version", "record")
    if not isinstance(software, str) or not software:
        raise RawDataValidationError("software must be a non-empty string")
    if not isinstance(software_version, str) or not software_version:
        raise RawDataValidationError("software_version must be a non-empty string")

    repetition = record["repetition"]
    if isinstance(repetition, bool) or not isinstance(repetition, int) or repetition < 1:
        raise RawDataValidationError("repetition must be a positive integer")

    command = record["command"]
    if not isinstance(command, list) or not command:
        raise RawDataValidationError("command must be a non-empty list")
    if not all(isinstance(part, str) and part for part in command):
        raise RawDataValidationError("every command item must be a non-empty string")

    metadata = record["metadata"]
    if not isinstance(metadata, dict):
        raise RawDataValidationError("metadata must be a JSON object")
    for field in ("execution_mode", "platform", "python_version"):
        value = _require(metadata, field, "metadata")
        if not isinstance(value, str) or not value.strip():
            raise RawDataValidationError(f"metadata.{field} must be a non-empty string")

    if "duration_ms" in record:
        duration = record["duration_ms"]
        if type(duration) not in (int, float) or duration < 0 or (
            isinstance(duration, float) and not math.isfinite(duration)
        ):
            raise RawDataValidationError("duration_ms must be a finite non-negative number")

    for field in ("stdout", "stderr"):
        if field in record and not isinstance(record[field], str):
            raise RawDataValidationError(f"{field} must be a string")

    returncode = record.get("returncode")
    if returncode is not None and type(returncode) is not int:
        raise RawDataValidationError("returncode must be an integer or null")
    if status == "success":
        if returncode != 0:
            raise RawDataValidationError("success records must have returncode 0")
    else:
        if returncode == 0:
            raise RawDataValidationError("error records cannot have returncode 0")
        error = record.get("error")
        if not isinstance(error, str) or not error:
            raise RawDataValidationError("error records must have a non-empty error")

    identifier = record.get("identifier")
    if identifier is None and source_path is not None:
        identifier = Path(source_path).stem
    if not isinstance(identifier, str) or not identifier:
        raise RawDataValidationError("identifier must be a non-empty string")

    source = record.get("source")
    if source is None:
        source = "local" if metadata.get("execution_mode") == "local" else "unknown"
    if not isinstance(source, str) or not source:
        raise RawDataValidationError("source must be a non-empty string")

    configuration = record.get("configuration")
    if configuration is None:
        configuration = {
            "execution_mode": metadata.get("execution_mode"),
            "timeout_seconds": metadata.get("timeout_seconds"),
        }
    if not isinstance(configuration, dict):
        raise RawDataValidationError("configuration must be a JSON object")

    return {
        **record,
        "identifier": identifier,
        "source": source,
        "configuration": configuration,
    }


def validate_raw_file(path: str | Path) -> dict[str, Any]:
    """Read and validate one raw JSON file without modifying it."""
    raw_path = Path(path)
    if not raw_path.is_file():
        raise RawDataValidationError(f"Raw data file not found: {raw_path}")
    try:
        record = json.loads(raw_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RawDataValidationError(f"Invalid JSON in {raw_path}: {exc.msg}") from exc
    return validate_pilot_record(record, source_path=raw_path)


def validate_raw_directory(directory: str | Path) -> list[dict[str, Any]]:
    """Validate every .json file in a raw directory; .tmp files are ignored."""
    raw_dir = Path(directory)
    if not raw_dir.is_dir():
        raise RawDataValidationError(f"Raw data directory not found: {raw_dir}")

    records: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*.json")):
        records.append(validate_raw_file(path))
    return records


def validate_record(record: object, *, source_path: str | Path | None = None) -> dict[str, Any]:
    """Short alias for validate_pilot_record."""
    return validate_pilot_record(record, source_path=source_path)


DataValidationError = RawDataValidationError
