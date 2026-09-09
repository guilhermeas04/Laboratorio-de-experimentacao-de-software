from __future__ import annotations

import csv
from pathlib import Path

import pytest

from lab02.counterbalance import (
    KATA_IDS,
    PARTICIPANTS,
    TrialAssignment,
    generate_design,
    main,
    validate_design,
    write_csv,
)


def rows_by_participant():
    rows = generate_design()
    return {
        participant: tuple(
            sorted(
                (row for row in rows if row.participant == participant),
                key=lambda row: row.execution_order,
            )
        )
        for participant in PARTICIPANTS
    }


def test_design_is_deterministic_and_has_eighteen_trials() -> None:
    first = generate_design()
    second = generate_design()

    assert first == second
    assert len(first) == 18
    assert len({row.trial_id for row in first}) == 18


def test_each_participant_has_all_katas_and_three_trials_per_treatment() -> None:
    grouped = rows_by_participant()

    assert set(grouped) == set(PARTICIPANTS)
    for rows in grouped.values():
        assert tuple(row.execution_order for row in rows) == tuple(range(1, 7))
        assert {row.kata_id for row in rows} == set(KATA_IDS)
        assert len({row.kata_id for row in rows}) == 6
        assert [row.treatment for row in rows].count("with_ai") == 3
        assert [row.treatment for row in rows].count("manual") == 3


def test_order_and_treatment_sequences_differ_between_participants() -> None:
    grouped = rows_by_participant()
    kata_orders = {tuple(row.kata_id for row in rows) for rows in grouped.values()}
    treatment_orders = {tuple(row.treatment for row in rows) for rows in grouped.values()}

    assert len(kata_orders) == 3
    assert len(treatment_orders) == 3


def test_trial_id_matches_collection_schema() -> None:
    rows = generate_design()

    assert rows[0].trial_id == "P01-K01-AI"
    assert rows[1].trial_id == "P01-K02-MANUAL"
    assert rows[6].trial_id == "P02-K03-MANUAL"


def test_validator_rejects_duplicate_kata() -> None:
    rows = list(generate_design())
    rows[1] = TrialAssignment("P01", "kata-01", "manual", 2)

    with pytest.raises(ValueError, match="cada kata exatamente uma vez"):
        validate_design(rows)


def test_validator_rejects_unbalanced_treatment() -> None:
    rows = list(generate_design())
    rows[1] = TrialAssignment("P01", "kata-02", "with_ai", 2)

    with pytest.raises(ValueError, match="três trials por tratamento"):
        validate_design(rows)


def test_csv_round_trip_and_cli_check(tmp_path: Path, capsys) -> None:
    output = tmp_path / "counterbalancing.csv"
    write_csv(generate_design(), output)

    with output.open(newline="", encoding="utf-8") as file:
        assert len(list(csv.DictReader(file))) == 18

    assert main(["--check", output]) == 0
    assert "válido: 18 trials" in capsys.readouterr().out
