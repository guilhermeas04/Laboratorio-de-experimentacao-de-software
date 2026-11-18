import json
import sys
from pathlib import Path

import pytest

from lab05_real_software.collector import (
    ExternalRequestLimiter,
    ExternalRequestNotAllowed,
    PilotCollector,
)


ROOT = Path(__file__).parents[1]
ETHICS_PATH = ROOT / "config" / "ethics.json"
STUDY_PATH = ROOT / "config" / "study.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "pilot_success.json"


@pytest.fixture
def ethics_config():
    return json.loads(ETHICS_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def study_config():
    return json.loads(STUDY_PATH.read_text(encoding="utf-8"))


def test_success_record_is_written_and_matches_fixture(tmp_path, ethics_config, study_config):
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    collector = PilotCollector(tmp_path, ethics_config, study_config)

    record = collector.collect_local(
        [sys.executable, "-c", "print('ok')"],
        software_version="fixture-15",
        repetition=1,
    )

    written = list(tmp_path.glob("*.json"))
    assert len(written) == 1
    assert json.loads(written[0].read_text(encoding="utf-8")) == record
    assert record["status"] == fixture["status"]
    assert record["software"] == "PostgreSQL"
    assert record["software_version"] == "fixture-15"
    assert record["repetition"] == 1
    assert record["returncode"] == 0
    assert record["stdout"].strip() == "ok"
    assert record["metadata"]["execution_mode"] == "local"


def test_command_failure_is_recorded_not_raised(tmp_path, ethics_config, study_config):
    collector = PilotCollector(tmp_path, ethics_config, study_config)

    record = collector.collect_local(
        [sys.executable, "-c", "raise RuntimeError('pilot failure')"],
        software_version="17",
        repetition=2,
    )

    assert record["status"] == "error"
    assert record["returncode"] != 0
    assert "pilot failure" in record["stderr"]
    assert record["error"] == "command exited with status 1"
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_missing_command_is_recorded_as_error(tmp_path, ethics_config, study_config):
    collector = PilotCollector(tmp_path, ethics_config, study_config)

    record = collector.collect_local(
        ["definitely-missing-lab05-command"],
        software_version="15",
        repetition=1,
    )

    assert record["status"] == "error"
    assert record["returncode"] is None
    assert "FileNotFoundError" in record["error"]


def test_empty_command_is_rejected(tmp_path, ethics_config, study_config):
    collector = PilotCollector(tmp_path, ethics_config, study_config)

    with pytest.raises(ValueError, match="cannot be empty"):
        collector.collect_local([], software_version="15", repetition=1)


def test_external_request_is_disabled_by_ethics_config(tmp_path, ethics_config, study_config):
    collector = PilotCollector(tmp_path, ethics_config, study_config)

    with pytest.raises(ExternalRequestNotAllowed, match="prohibited"):
        collector.fetch_external("https://example.invalid", lambda *_args, **_kwargs: None)


def test_external_limiter_waits_at_least_one_second():
    calls = []
    now = [100.0]

    def clock():
        return now[0]

    def sleep(seconds):
        calls.append(seconds)
        now[0] += seconds

    config = {"external_requests": {"allowed": True, "max_per_second": 1}}
    limiter = ExternalRequestLimiter(config, clock=clock, sleeper=sleep)

    limiter.wait()
    limiter.wait()

    assert len(calls) == 1
    assert calls[0] == pytest.approx(1.0)


def test_external_limiter_rejects_more_than_one_per_second():
    config = {"external_requests": {"allowed": True, "max_per_second": 2}}

    with pytest.raises(ExternalRequestNotAllowed, match="no more than one"):
        ExternalRequestLimiter(config).wait()
