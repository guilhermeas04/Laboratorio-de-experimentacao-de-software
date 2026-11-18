import json
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
CONFIG_PATH = ROOT / "config" / "ethics.json"
REQUIRED_TOP_LEVEL_FIELDS = {"study_scope", "external_requests", "participants", "data_protection"}


def load_ethics_config(path=CONFIG_PATH):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = REQUIRED_TOP_LEVEL_FIELDS - config.keys()
    if missing:
        raise ValueError(f"missing ethics fields: {', '.join(sorted(missing))}")
    if config["external_requests"]["load_testing_third_party_systems"]:
        raise ValueError("third-party load testing must be disabled")
    if config["participants"]["real_accounts_or_data_allowed"]:
        raise ValueError("real accounts or data must be disabled")
    if config["data_protection"]["collect_personal_data"]:
        raise ValueError("personal data collection must be disabled")
    return config


def test_official_ethics_configuration_is_safe():
    config = load_ethics_config()

    assert config["participants"]["involved"] is False
    assert config["external_requests"]["allowed"] is False
    assert config["data_protection"]["store_secrets_in_repository"] is False
    assert config["operational_safeguards"]


def test_missing_required_field_is_rejected(tmp_path):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    del config["data_protection"]
    path = tmp_path / "invalid-ethics.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="data_protection"):
        load_ethics_config(path)


def test_third_party_load_testing_is_rejected(tmp_path):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["external_requests"]["load_testing_third_party_systems"] = True
    path = tmp_path / "invalid-ethics.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="third-party load testing"):
        load_ethics_config(path)
