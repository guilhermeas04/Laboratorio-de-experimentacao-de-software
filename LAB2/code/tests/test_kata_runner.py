from __future__ import annotations

from pathlib import Path

import pytest

from lab02.kata_catalog import KATAS
from lab02.kata_runner import main


def test_catalog_has_six_balanced_katas_with_unique_cases() -> None:
    assert [kata.kata_id for kata in KATAS] == [f"kata-{index:02d}" for index in range(1, 7)]
    assert {len(kata.cases) for kata in KATAS} == {5}
    for kata in KATAS:
        assert len({case.name for case in kata.cases}) == len(kata.cases)
        assert sum(case.invalid for case in kata.cases) == 1


def test_runner_executes_only_selected_kata(tmp_path: Path, capsys) -> None:
    solution = tmp_path / "candidate.py"
    solution.write_text(
        """def solve(value):
    text = value[\"text\"]
    if not isinstance(text, str):
        raise ValueError
    counts = {char: text.count(char) for char in text}
    return next((index for index, char in enumerate(text) if counts[char] == 1), -1)
""",
        encoding="utf-8",
    )

    assert main([str(solution), "--kata-id", "kata-02"]) == 0
    output = capsys.readouterr().out
    assert "total=5 passing=5 failing=0" in output
    assert "kata-01" not in output


def test_runner_requires_kata_id(tmp_path: Path) -> None:
    solution = tmp_path / "candidate.py"
    solution.write_text("def solve(value): return value\n", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main([str(solution)])
    assert error.value.code == 2


def test_runner_reports_module_load_failure(tmp_path: Path, capsys) -> None:
    solution = tmp_path / "candidate.py"
    solution.write_text("raise RuntimeError('broken import')\n", encoding="utf-8")

    assert main([str(solution), "--kata-id", "kata-01"]) == 2
    assert "broken import" in capsys.readouterr().out
