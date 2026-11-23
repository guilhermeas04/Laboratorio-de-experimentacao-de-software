import copy
import json

import pytest

from lab05_real_software.s02_dataset import (
    CampaignValidationError,
    validate_campaign,
    write_processed_dataset,
)


CONFIG = {
    "versions": ["15.20", "17.12"],
    "seed": 150,
    "dataset_rows": 100000,
    "blocks": 1,
    "cpus": 1,
    "memory_mb": 512,
    "shared_buffers_mb": 128,
    "clients": 4,
    "jobs": 1,
    "warmup_seconds": 5,
    "server_latency_repetitions": 5,
    "measurement_seconds": 15,
    "sample_interval_seconds": 1,
}


def make_campaign(tmp_path, statuses=None):
    campaign = tmp_path / "campaign"
    rounds = campaign / "rounds"
    rounds.mkdir(parents=True)
    statuses = statuses or {}
    planned = [
        {"block": 1, "position": 1, "software_version": "15.20", "scenario": "customer_total"},
        {"block": 1, "position": 2, "software_version": "17.12", "scenario": "customer_total"},
    ]
    images = {"15.20": "image-15", "17.12": "image-17"}
    manifest = {
        "schema_version": "lab05-s02-campaign-v1",
        "campaign_id": "test-campaign",
        "status": "complete",
        "configuration": CONFIG,
        "environment": {"images": images},
        "planned_rounds": planned,
        "counts": {"planned": 2, "recorded": 2, "successful": 2, "failed": 0,
                   "accepted_blocks": 1, "accepted_rounds": 2, "pending_rounds": 0},
        "attempts": [{
            "execution_id": "test-campaign-b001-a01",
            "block": 1,
            "status": "accepted",
            "records": [],
        }],
    }
    for item in planned:
        version = item["software_version"]
        status = statuses.get(version, "success")
        round_id = f"test-campaign-b001-a01-b001-p{item['position']}-customer_total"
        relative = f"rounds/{round_id}.json"
        record = {
            "schema_version": "lab05-s02-round-v1",
            "execution_id": "test-campaign-b001-a01",
            "round_id": round_id,
            "block": 1,
            "position": item["position"],
            "software_version": version,
            "scenario": "customer_total",
            "configuration": CONFIG,
            "collected_at": "2026-11-21T21:04:01+00:00",
            "ended_at": "2026-11-21T21:04:25+00:00",
            "status": status,
            "campaign_id": "test-campaign",
            "image_id": images[version],
            "server_version": f"{version} (Debian)",
            "metrics": {
                "query_latency_ms": 0.4,
                "throughput_queries_per_second": 5000.0,
                "cpu_percent": 50.0,
                "memory_mb": 80.0,
                "client_latency_ms": 0.8,
                "resource_window_seconds": 15.5,
            },
        }
        if status == "error":
            record["error"] = "synthetic failure"
        (campaign / relative).write_text(json.dumps(record), encoding="utf-8")
        manifest["attempts"][0]["records"].append({"file": relative, "status": status})
    (campaign / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return campaign


def test_valid_records_generate_dataset(tmp_path):
    campaign = make_campaign(tmp_path)
    _, rows, failures = validate_campaign(campaign)
    assert len(rows) == 2
    assert failures == []


def test_duplicate_record_is_excluded(tmp_path):
    campaign = make_campaign(tmp_path)
    manifest_path = campaign / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    record_entry = copy.deepcopy(manifest["attempts"][0]["records"][1])
    manifest["attempts"][0]["records"].append(record_entry)
    manifest_path.write_text(json.dumps(manifest))

    _, rows, failures = validate_campaign(campaign)
    assert len(rows) == 2
    assert any("duplicate" in failure["reason"] for failure in failures)


def test_invalid_metric_is_excluded(tmp_path):
    campaign = make_campaign(tmp_path)
    relative = campaign / "rounds/test-campaign-b001-a01-b001-p1-customer_total.json"
    record = json.loads(relative.read_text())
    record["metrics"]["query_latency_ms"] = -1
    relative.write_text(json.dumps(record))

    _, rows, failures = validate_campaign(campaign)
    assert len(rows) == 1
    assert any("outside" in failure["reason"] for failure in failures)


def test_incomplete_pair_is_reported(tmp_path):
    campaign = make_campaign(tmp_path, statuses={"17.12": "error"})
    report = write_processed_dataset(campaign, tmp_path / "processed")
    assert report["counts"]["excluded_rounds"] == 1
    incomplete = report["incomplete_pairs"]
    assert any(item["metric"] == "query_latency_ms" and item["missing_versions"] == ["17.12"] for item in incomplete)


def test_campaign_must_be_complete(tmp_path):
    campaign = make_campaign(tmp_path)
    manifest_path = campaign / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "incomplete"
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(CampaignValidationError, match="not complete"):
        validate_campaign(campaign)


def test_planned_position_and_exact_version_are_validated(tmp_path):
    campaign = make_campaign(tmp_path)
    path = sorted((campaign / "rounds").glob("*.json"))[0]
    record = json.loads(path.read_text())
    record.update(position=99, server_version="15.200 (Debian)")
    path.write_text(json.dumps(record))
    _, rows, failures = validate_campaign(campaign)
    assert len(rows) == 1
    assert "position differs" in failures[0]["reason"]
    assert "server version differs" in failures[0]["reason"]


def test_missing_both_rounds_appears_in_pairs_and_missing_counts(tmp_path):
    campaign = make_campaign(tmp_path)
    for path in (campaign / "rounds").glob("*.json"):
        path.unlink()
    report = write_processed_dataset(campaign, tmp_path / "processed")
    assert report["counts"]["excluded_rounds"] == 2
    assert report["missing_by_metric"]["query_latency_ms"] == 2
    assert all(pair["missing_versions"] == ["15.20", "17.12"] for pair in report["incomplete_pairs"])
    assert len(report["incomplete_pairs"]) == 6


def test_missing_metric_counts_excluded_round_as_unavailable(tmp_path):
    campaign = make_campaign(tmp_path)
    path = sorted((campaign / "rounds").glob("*.json"))[0]
    record = json.loads(path.read_text())
    del record["metrics"]["query_latency_ms"]
    path.write_text(json.dumps(record))
    report = write_processed_dataset(campaign, tmp_path / "processed")
    assert report["missing_by_metric"]["query_latency_ms"] == 1
    assert report["counts"]["accepted_blocks"] == 0


def test_manifest_reconciliation_reports_counts_status_and_extra_files(tmp_path):
    campaign = make_campaign(tmp_path)
    path = campaign / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["counts"]["planned"] = 99
    manifest["attempts"][0]["records"][0]["status"] = "error"
    path.write_text(json.dumps(manifest))
    (campaign / "rounds" / "extra.json").write_text("{}")
    _, rows, failures = validate_campaign(campaign)
    assert len(rows) == 1
    problems = [failure["reason"] for failure in failures if failure["classification"] == "manifest"]
    assert any("counts.planned" in reason for reason in problems)
    assert any("raw status differs" in reason for reason in problems)
    assert any("not tracked" in reason for reason in problems)


def test_failed_attempt_remains_visible_without_excluding_accepted_slots(tmp_path):
    campaign = make_campaign(tmp_path)
    path = campaign / "manifest.json"
    manifest = json.loads(path.read_text())
    relative = "rounds/failed.json"
    (campaign / relative).write_text(json.dumps({"status": "error", "error": "timeout"}))
    manifest["attempts"].append({
        "block": 1, "status": "failed", "execution_id": "failed",
        "records": [{"file": relative, "status": "error"}],
    })
    manifest["counts"].update(recorded=3, failed=1)
    path.write_text(json.dumps(manifest))
    report = write_processed_dataset(campaign, tmp_path / "processed")
    assert report["counts"]["excluded_rounds"] == 0
    assert report["failures"] == [{"source": relative, "classification": "attempt", "reason": "timeout"}]
