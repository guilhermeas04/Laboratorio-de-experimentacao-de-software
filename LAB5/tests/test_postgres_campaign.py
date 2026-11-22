import json

import pytest

from lab05_real_software import postgres_campaign as campaign


@pytest.mark.parametrize("interruption", ["error", "interrupt"])
def test_resume_keeps_attempts_and_accepts_only_complete_blocks(tmp_path, monkeypatch, interruption):
    config = {"versions": ["15.20", "17.12"], "blocks": 2, "queries": {"sum": "SELECT 1;"}, "seed": 150}
    images = {version: f"image-{version}" for version in config["versions"]}
    monkeypatch.setattr(campaign, "environment_snapshot", lambda _: {"images": images})
    monkeypatch.setattr(campaign, "docker", lambda *args: "")
    attempts = []

    def run_round(config, destination, *, block, position, version, scenario, execution_id, campaign_id):
        attempts.append((block, position))
        first_attempt = len(attempts) == 2
        if first_attempt and interruption == "interrupt":
            raise KeyboardInterrupt
        round_id = f"{execution_id}-b{block:03d}-p{position}-{scenario}"
        record = {
            "campaign_id": campaign_id, "block": block, "position": position,
            "software_version": version, "scenario": scenario, "execution_id": execution_id,
            "round_id": round_id, "configuration": config, "image_id": images[version],
            "status": "error" if first_attempt else "success",
        }
        if first_attempt:
            record["error"] = "synthetic test failure"
        (destination / f"{round_id}.json").write_text(json.dumps(record), encoding="utf-8")
        return record

    monkeypatch.setattr(campaign, "run_round", run_round)
    destination = tmp_path / "test"
    assert campaign.run_campaign(config, destination, "test", resume=False) == 1
    previous = {path.name: path.read_bytes() for path in (destination / "rounds").glob("*.json")}
    assert campaign.run_campaign(config, destination, "test", resume=True) == 0
    assert all((destination / "rounds" / name).read_bytes() == body for name, body in previous.items())
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["accepted_rounds"] == manifest["counts"]["planned"] == 4
    assert manifest["counts"]["recorded"] == manifest["counts"]["successful"] + manifest["counts"]["failed"]
    assert manifest["counts"]["pending_rounds"] == 0
    assert [entry["status"] for entry in manifest["attempts"]] == [
        "failed" if interruption == "error" else "interrupted", "accepted", "accepted"
    ]
    assert campaign.run_campaign(config, destination, "test", resume=True) == 0
    assert len(attempts) == 6
