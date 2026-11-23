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
