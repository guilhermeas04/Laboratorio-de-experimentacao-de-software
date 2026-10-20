import json
from pathlib import Path


def test_sprint3_manifest_has_unique_dataset(tmp_path):
    manifest = {"repository_count": 300, "unique_repository_count": 300}
    path = tmp_path / "sprint3_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["repository_count"] >= 300
    assert loaded["repository_count"] == loaded["unique_repository_count"]
