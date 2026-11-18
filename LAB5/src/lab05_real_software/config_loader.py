"""Load and validate the LAB5 study configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StudyConfigError(ValueError):
    """Raised when a study configuration is missing or invalid."""


REQUIRED_STUDY_FIELDS = {"title", "objective", "research_question", "goal", "metrics"}
REQUIRED_GOAL_FIELDS = {"analyze", "for_purpose", "with_respect_to", "from_viewpoint_of", "in_context_of"}
REQUIRED_SOFTWARE_FIELDS = {"name", "versions", "execution_mode"}
REQUIRED_EVIDENCE_FIELDS = {"criterion", "claim", "sources"}
REQUIRED_CRITERIA = {"real", "in_operation", "high_impact"}


def load_study_config(path: str | Path) -> dict[str, Any]:
    """Read a JSON study configuration and validate its research contract."""

    config_path = Path(path)
    if not config_path.is_file():
        raise StudyConfigError(f"Configuration file not found: {config_path}")

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StudyConfigError(f"Invalid JSON in {config_path}: {exc.msg}") from exc

    validate_study_config(config)
    return config


def validate_study_config(config: object) -> None:
    """Validate required fields and the three software evidence criteria."""

    if not isinstance(config, dict):
        raise StudyConfigError("Configuration root must be a JSON object")

    software = _object(config.get("software"), "software")
    _require_fields(software, REQUIRED_SOFTWARE_FIELDS, "software")
    versions = software["versions"]
    if not isinstance(versions, list) or len(versions) < 2 or not all(isinstance(v, str) and v for v in versions):
        raise StudyConfigError("software.versions must contain at least two non-empty strings")

    study = _object(config.get("study"), "study")
    _require_fields(study, REQUIRED_STUDY_FIELDS, "study")
    goal = _object(study.get("goal"), "study.goal")
    _require_fields(goal, REQUIRED_GOAL_FIELDS, "study.goal")
    metrics = study["metrics"]
    if not isinstance(metrics, list) or not metrics:
        raise StudyConfigError("study.metrics must be a non-empty list")
    for index, metric in enumerate(metrics):
        metric_object = _object(metric, f"study.metrics[{index}]")
        _require_fields(metric_object, {"name", "description", "scale", "type"}, f"study.metrics[{index}]")

    evidence = config.get("evidence")
    if not isinstance(evidence, list):
        raise StudyConfigError("evidence must be a list")
    criteria = set()
    for index, item in enumerate(evidence):
        evidence_object = _object(item, f"evidence[{index}]")
        _require_fields(evidence_object, REQUIRED_EVIDENCE_FIELDS, f"evidence[{index}]")
        if not isinstance(evidence_object["sources"], list) or not evidence_object["sources"]:
            raise StudyConfigError(f"evidence[{index}].sources must be a non-empty list")
        criteria.add(evidence_object["criterion"])
    missing_criteria = REQUIRED_CRITERIA - criteria
    if missing_criteria:
        raise StudyConfigError(f"Missing evidence criteria: {', '.join(sorted(missing_criteria))}")


def _object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StudyConfigError(f"{field} must be an object")
    return value


def _require_fields(value: dict[str, Any], fields: set[str], prefix: str) -> None:
    missing = fields - value.keys()
    if missing:
        raise StudyConfigError(f"{prefix} is missing: {', '.join(sorted(missing))}")
