"""Deterministic crossover design and validation for the LAB02 experiment."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

KATA_IDS = tuple(f"kata-{index:02d}" for index in range(1, 7))
PARTICIPANTS = ("P01", "P02", "P03")
TREATMENTS = ("with_ai", "manual")

_KATA_ORDERS = (
    ("kata-01", "kata-02", "kata-03", "kata-04", "kata-05", "kata-06"),
    ("kata-03", "kata-04", "kata-05", "kata-06", "kata-01", "kata-02"),
    ("kata-05", "kata-06", "kata-01", "kata-02", "kata-03", "kata-04"),
)
_TREATMENT_ORDERS = (
    ("with_ai", "manual", "with_ai", "manual", "with_ai", "manual"),
    ("manual", "with_ai", "manual", "with_ai", "manual", "with_ai"),
    ("with_ai", "with_ai", "manual", "manual", "with_ai", "manual"),
)


@dataclass(frozen=True, slots=True)
class TrialAssignment:
    participant: str
    kata_id: str
    treatment: str
    execution_order: int

    @property
    def trial_id(self) -> str:
        suffix = "AI" if self.treatment == "with_ai" else "MANUAL"
        kata_number = self.kata_id.rsplit("-", maxsplit=1)[1]
        return f"{self.participant}-K{kata_number}-{suffix}"

    def to_dict(self) -> dict[str, str | int]:
        return {
            "participant": self.participant,
            "kata_id": self.kata_id,
            "treatment": self.treatment,
            "execution_order": self.execution_order,
            "trial_id": self.trial_id,
        }


def generate_design() -> tuple[TrialAssignment, ...]:
    """Generate the fixed 3-participant, 6-kata crossover allocation."""

    assignments = tuple(
        TrialAssignment(participant, kata_id, treatment, position)
        for participant, kata_order, treatment_order in zip(
            PARTICIPANTS, _KATA_ORDERS, _TREATMENT_ORDERS
        )
        for position, (kata_id, treatment) in enumerate(
            zip(kata_order, treatment_order), start=1
        )
    )
    validate_design(assignments)
    return assignments


def validate_design(assignments: Iterable[TrialAssignment]) -> None:
    """Raise ValueError unless all issue #52 allocation invariants hold."""

    rows = tuple(assignments)
    participants = tuple(dict.fromkeys(row.participant for row in rows))
    if participants != PARTICIPANTS:
        raise ValueError(f"participantes esperados: {PARTICIPANTS!r}")
    if len(rows) != 18:
        raise ValueError("o desenho deve conter 18 trials")

    orders: list[tuple[str, ...]] = []
    treatments: list[tuple[str, ...]] = []
    for participant in PARTICIPANTS:
        participant_rows = tuple(
            sorted(
                (row for row in rows if row.participant == participant),
                key=lambda row: row.execution_order,
            )
        )
        if len(participant_rows) != 6:
            raise ValueError(f"{participant} deve ter seis trials")
        if tuple(row.execution_order for row in participant_rows) != tuple(range(1, 7)):
            raise ValueError(f"ordem inválida para {participant}")
        kata_order = tuple(row.kata_id for row in participant_rows)
        if kata_order != tuple(dict.fromkeys(kata_order)) or set(kata_order) != set(KATA_IDS):
            raise ValueError(f"{participant} deve resolver cada kata exatamente uma vez")
        treatment_order = tuple(row.treatment for row in participant_rows)
        if any(treatment not in TREATMENTS for treatment in treatment_order):
            raise ValueError(f"tratamento inválido para {participant}")
        if treatment_order.count("with_ai") != 3 or treatment_order.count("manual") != 3:
            raise ValueError(f"{participant} deve ter três trials por tratamento")
        orders.append(kata_order)
        treatments.append(treatment_order)

    if len(set(orders)) != len(orders):
        raise ValueError("ordens de kata não podem ser idênticas entre participantes")
    if len(set(treatments)) != len(treatments):
        raise ValueError("ordens de tratamento não podem ser idênticas entre participantes")
    if len({row.trial_id for row in rows}) != len(rows):
        raise ValueError("trial_id duplicado")


def write_csv(assignments: Sequence[TrialAssignment], output: Path) -> None:
    """Write an auditable allocation table without participant result data."""

    validate_design(assignments)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=("participant", "execution_order", "kata_id", "treatment", "trial_id"),
        )
        writer.writeheader()
        writer.writerows(
            {
                "participant": row.participant,
                "execution_order": row.execution_order,
                "kata_id": row.kata_id,
                "treatment": row.treatment,
                "trial_id": row.trial_id,
            }
            for row in assignments
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera a ordem contrabalanceada do LAB02")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path, help="valida uma tabela CSV existente")
    args = parser.parse_args(argv)

    if args.check:
        with args.check.open(newline="", encoding="utf-8") as file:
            rows = tuple(
                TrialAssignment(
                    participant=row["participant"],
                    kata_id=row["kata_id"],
                    treatment=row["treatment"],
                    execution_order=int(row["execution_order"]),
                )
                for row in csv.DictReader(file)
            )
        validate_design(rows)
        print(f"válido: {len(rows)} trials")
        return 0

    if args.output is None:
        parser.error("--output é obrigatório ao gerar uma tabela")
    assignments = generate_design()
    write_csv(assignments, args.output)
    print(f"gerado: {len(assignments)} trials em {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
