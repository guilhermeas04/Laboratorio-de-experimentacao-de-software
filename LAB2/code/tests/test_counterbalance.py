from __future__ import annotations

import csv
from pathlib import Path

import pytest

from lab02.counterbalance import (
    KATA_IDS,
    KATA_PAIRS,
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
        treatment_by_kata = {row.kata_id: row.treatment for row in rows}
        for first, second in KATA_PAIRS:
            assert {treatment_by_kata[first], treatment_by_kata[second]} == {
                "with_ai",
                "manual",
            }


def test_order_and_treatment_sequences_differ_between_participants() -> None:
    grouped = rows_by_participant()
    kata_orders = {tuple(row.kata_id for row in rows) for rows in grouped.values()}
    treatment_orders = {tuple(row.treatment for row in rows) for rows in grouped.values()}

    assert len(kata_orders) == 3
    assert len(treatment_orders) == 3


def test_treatment_is_balanced_by_position_and_kata() -> None:
    rows = generate_design()

    for position in range(1, 7):
        assert sum(
            row.treatment == "with_ai" for row in rows if row.execution_order == position
        ) in (1, 2)
    for kata_id in KATA_IDS:
        assert sum(row.treatment == "with_ai" for row in rows if row.kata_id == kata_id) in (1, 2)


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

    assert main(["--check", str(output)]) == 0
    assert "válido: 18 trials" in capsys.readouterr().out


def test_validator_rejects_same_treatment_inside_matched_pair() -> None:
    rows = list(generate_design())
    rows[0] = TrialAssignment("P01", "kata-01", "manual", 1)
    rows[3] = TrialAssignment("P01", "kata-04", "with_ai", 4)

    with pytest.raises(ValueError, match="tratamentos opostos"):
        validate_design(rows)


def test_cli_reports_invalid_csv_without_traceback(tmp_path: Path, capsys) -> None:
    invalid = tmp_path / "invalid.csv"
    invalid.write_text("participant,execution_order\nP01,wrong\n", encoding="utf-8")

    assert main(["--check", str(invalid)]) == 1
    assert "tabela de contrabalanceamento inválida" in capsys.readouterr().out
