"""Gera uma visão da amostra-ouro sem casos sem release.

Uso: python scripts/filter_evaluable_labels.py entrada.csv saida.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from lab03_dora.validation.labels import evaluable_labels


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("uso: python scripts/filter_evaluable_labels.py entrada.csv saida.csv")
    source, destination = map(Path, sys.argv[1:])
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = evaluable_labels(reader)
        fields = reader.fieldnames or []
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"linhas avaliáveis: {len(rows)}; saída: {destination}")


if __name__ == "__main__":
    main()
