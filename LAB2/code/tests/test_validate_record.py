from __future__ import annotations

import json
from pathlib import Path

from lab02.validate_record import main


def test_cli_accepts_valid_json(tmp_path: Path, capsys) -> None:
    record_path = tmp_path / "trial.json"
    record_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "trial_id": "P01-K01-MANUAL",
                "participant": "participant-01",
                "kata_id": "kata-01",
                "treatment": "manual",
                "execution_order": 1,
                "started_at": "2026-09-08T19:00:00-03:00",
                "finished_at": "2026-09-08T19:35:00-03:00",
                "elapsed_seconds": 2100,
                "time_to_green_seconds": None,
                "censored": True,
                "tests_total": 10,
                "tests_passing": 8,
                "success_rate": 80,
            }
        ),
        encoding="utf-8",
    )

    assert main([str(record_path)]) == 0
    assert "trial P01-K01-MANUAL válido" in capsys.readouterr().out


def test_cli_rejects_invalid_json(tmp_path: Path, capsys) -> None:
    record_path = tmp_path / "trial.json"
    record_path.write_text("[]", encoding="utf-8")

    assert main([str(record_path)]) == 1
    assert "raiz do JSON deve ser um objeto" in capsys.readouterr().out
