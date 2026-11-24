import json
from pathlib import Path
import shutil

from lab05_real_software.s02_validity import diagnose_validity


ROOT = Path(__file__).parents[1]
CAMPAIGN = ROOT / "data" / "raw" / "s02" / "lab05s02-20261121-01"
DATASET = ROOT / "data" / "processed" / "lab05s02-20261121-01_validated.csv"
QUALITY = ROOT / "data" / "processed" / "lab05s02-20261121-01_quality.json"


def test_configuration_drift_in_raw_record_is_flagged(tmp_path):
    campaign_copy = tmp_path / "campaign"
    (campaign_copy / "rounds").mkdir(parents=True)
    manifest = json.loads((CAMPAIGN / "manifest.json").read_text(encoding="utf-8"))
    attempt = manifest["attempts"][0]
    entry = attempt["records"][0]
    source = CAMPAIGN / entry["file"]
    destination = campaign_copy / entry["file"]
    shutil.copyfile(source, destination)

    record = json.loads(destination.read_text(encoding="utf-8"))
    record["configuration"]["memory_mb"] += 1
    destination.write_text(json.dumps(record), encoding="utf-8")
    attempt["records"] = [entry]
    manifest["attempts"] = [attempt]
    (campaign_copy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    paths = diagnose_validity(
        dataset_path=DATASET,
        campaign_dir=campaign_copy,
        quality_path=QUALITY,
        output_dir=tmp_path / "diagnostics",
    )
    report = json.loads(paths["summary"].read_text(encoding="utf-8"))

    assert report["consistency"]["consistent"] is False
    assert any("configuration differs" in issue["issue"] for issue in report["consistency"]["issues"])
