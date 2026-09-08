from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lab02.trial_cli import main


def paths(tmp_path: Path) -> list[str]:
    return ["--sessions-dir", str(tmp_path / "sessions"), "--output-dir", str(tmp_path / "raw")]


def test_cli_starts_and_reads_trial_status(tmp_path: Path, capsys) -> None:
    start_args = paths(tmp_path) + [
        "start",
        "--trial-id",
        "P01-K01-MANUAL",
        "--participant",
        "participant-01",
        "--kata-id",
        "kata-01",
        "--treatment",
        "manual",
        "--execution-order",
        "1",
    ]

    assert main(start_args) == 0
    assert "INICIADO: P01-K01-MANUAL" in capsys.readouterr().out
    assert main(paths(tmp_path) + ["status", "--trial-id", "P01-K01-MANUAL"]) == 0
    assert "STATUS: P01-K01-MANUAL" in capsys.readouterr().out


def test_cli_finishes_censored_trial(tmp_path: Path, capsys) -> None:
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    started_at = datetime.now(timezone.utc) - timedelta(minutes=36)
    (session_dir / "P01-K01-MANUAL.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "trial_id": "P01-K01-MANUAL",
                "participant": "participant-01",
                "kata_id": "kata-01",
                "treatment": "manual",
                "execution_order": 1,
                "started_at": started_at.isoformat(),
                "assistant_name": None,
                "assistant_version": None,
            }
        ),
        encoding="utf-8",
    )

    result = main(
        paths(tmp_path)
        + [
            "finish",
            "--trial-id",
            "P01-K01-MANUAL",
            "--tests-total",
            "10",
            "--tests-passing",
            "8",
        ]
    )

    assert result == 0
    assert "CENSURADO: P01-K01-MANUAL" in capsys.readouterr().out
    record = json.loads((tmp_path / "raw" / "P01-K01-MANUAL.json").read_text(encoding="utf-8"))
    assert record["elapsed_seconds"] == 2100
    assert record["success_rate"] == 80


def test_cli_returns_error_for_unknown_trial(tmp_path: Path, capsys) -> None:
    result = main(paths(tmp_path) + ["status", "--trial-id", "UNKNOWN"])

    assert result == 1
    assert "não foi iniciado" in capsys.readouterr().out
