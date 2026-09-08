from __future__ import annotations

import json
from pathlib import Path

from lab02.environment_check import DEMO_TRIAL_ID, EnvironmentChecker
from lab02.smoke_cli import main


def test_smoke_command_passes_and_isolates_demo(tmp_path: Path, capsys) -> None:
    lab2_root = tmp_path / "LAB2"
    for relative in (
        "code/tests/fixtures/metrics/valid",
        "data/examples",
        "data/raw",
        "data/processed",
        "data/sessions",
        "data/demo",
        "docs",
        "reports",
    ):
        (lab2_root / relative).mkdir(parents=True)

    sample = lab2_root / "code/tests/fixtures/metrics/valid/sample.py"
    sample.write_text("def score(n):\n    return n + 1\n", encoding="utf-8")

    demo_dir = lab2_root / "data" / "demo"
    checker = EnvironmentChecker(lab2_root=lab2_root, demo_dir=demo_dir)
    report = checker.run()

    assert report.ok
    assert report.demo_trial_path is not None
    assert report.demo_metrics_path is not None
    assert DEMO_TRIAL_ID in report.demo_trial_path.name
    assert not (lab2_root / "data" / "raw" / f"{DEMO_TRIAL_ID}.json").exists()
    assert report.demo_trial_path.exists()

    trial = json.loads(report.demo_trial_path.read_text(encoding="utf-8"))
    assert trial["trial_id"] == DEMO_TRIAL_ID
    assert trial["censored"] is False


def test_smoke_detects_missing_radon(monkeypatch, tmp_path: Path) -> None:
    lab2_root = tmp_path / "LAB2"
    for relative in (
        "code",
        "data/examples",
        "data/raw",
        "data/processed",
        "data/sessions",
        "data/demo",
        "docs",
        "reports",
    ):
        (lab2_root / relative).mkdir(parents=True)

    checker = EnvironmentChecker(lab2_root=lab2_root, demo_dir=lab2_root / "data" / "demo")
    monkeypatch.setattr("lab02.environment_check.importlib.util.find_spec", lambda name: None)
    report = checker.run()

    radon_check = next(check for check in report.checks if check.name == "radon")
    assert radon_check.ok is False
    assert "ausente" in radon_check.detail
    assert report.ok is False


def test_smoke_cli_returns_zero_on_success(capsys) -> None:
    assert main([]) == 0
    output = capsys.readouterr().out
    assert "RESULTADO: ambiente pronto" in output
    assert "DEMO-SMOKE-P00-K00-MANUAL" in output
