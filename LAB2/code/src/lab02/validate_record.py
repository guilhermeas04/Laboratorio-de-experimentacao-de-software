"""CLI mínima para validar um registro JSON sem alterar dados."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .trial_record import TrialRecord, TrialValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida um registro JSON de trial do LAB02.")
    parser.add_argument("record", type=Path, help="Caminho do registro JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with args.record.open(encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            raise TrialValidationError("a raiz do JSON deve ser um objeto")
        record = TrialRecord.from_mapping(payload)
    except (OSError, json.JSONDecodeError, TrialValidationError) as error:
        print(f"ERRO: {error}")
        return 1

    print(f"OK: trial {record.trial_id} válido (schema {record.schema_version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
