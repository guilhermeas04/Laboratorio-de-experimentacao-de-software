import json
from pathlib import Path

import pytest

from lab05_real_software.config_loader import StudyConfigError, load_study_config


ROOT = Path(__file__).parents[1]
CONFIG_PATH = ROOT / "config" / "study.json"


def test_official_study_configuration_is_valid():
    config = load_study_config(CONFIG_PATH)

    assert config["software"]["name"] == "PostgreSQL"
    assert config["software"]["versions"] == ["15", "17"]
    assert {item["criterion"] for item in config["evidence"]} == {
        "real",
        "in_operation",
        "high_impact",
    }


def test_missing_research_question_is_rejected(tmp_path):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    del config["study"]["research_question"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(StudyConfigError, match="research_question"):
        load_study_config(path)


def test_missing_impact_evidence_is_rejected(tmp_path):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["evidence"] = [item for item in config["evidence"] if item["criterion"] != "high_impact"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(StudyConfigError, match="high_impact"):
        load_study_config(path)


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(StudyConfigError, match="not found"):
        load_study_config(tmp_path / "missing.json")
