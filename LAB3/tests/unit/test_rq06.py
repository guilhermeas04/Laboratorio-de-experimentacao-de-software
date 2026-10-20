import csv
import json
from xml.etree import ElementTree

import pytest

from lab03_dora.analysis.rq06 import (
    analyze,
    cliffs_delta,
    cliffs_magnitude,
    compare_groups,
    epsilon_magnitude,
    epsilon_squared,
    holm,
    language_groups,
    main,
    quartile_groups,
)
from lab03_dora.collection.repository_metadata import age_in_years, contributor_count


def test_quartile_groups_keep_missing_out() -> None:
    labels, cuts = quartile_groups([1, 2, 3, 4, 5, 6, 7, 8, None])

    assert labels == ["Q1", "Q1", "Q2", "Q2", "Q3", "Q3", "Q4", "Q4", ""]
    assert cuts == [2.75, 4.5, 6.25]


def test_small_and_empty_languages_become_other() -> None:
    languages = ["Python"] * 3 + ["Go"] + [""]

    assert language_groups(languages, minimum=2) == ["Python", "Python", "Python", "Outras", "Outras"]


def test_effect_sizes_follow_the_assignment_formulas() -> None:
    assert epsilon_squared(9.0, 31) == pytest.approx(0.3)
    assert cliffs_delta([4, 5, 6], [1, 2, 3]) == pytest.approx(1.0)
    assert cliffs_delta([1, 2, 3], [4, 5, 6]) == pytest.approx(-1.0)
    assert cliffs_delta([1, 2], [1, 2]) == pytest.approx(0.0)
    assert cliffs_magnitude(0.1) == "desprezivel"
    assert cliffs_magnitude(-0.2) == "pequeno"
    assert cliffs_magnitude(0.4) == "medio"
    assert cliffs_magnitude(0.5) == "grande"
    assert epsilon_magnitude(0.005) == "desprezivel"
    assert epsilon_magnitude(0.3) == "grande"


def test_holm_matches_manual_adjustment_and_keeps_missing() -> None:
    adjusted = holm([0.01, None, 0.04, 0.03])

    # Ordenados: 0.01*3, 0.03*2, 0.04*1, com monotonia.
    assert adjusted[0] == pytest.approx(0.03)
    assert adjusted[1] is None
    assert adjusted[3] == pytest.approx(0.06)
    assert adjusted[2] == pytest.approx(0.06)


def test_compare_groups_uses_kruskal_and_skips_missing() -> None:
    rows = [{"g": "A", "m": str(value)} for value in (1, 2, 3)]
    rows += [{"g": "B", "m": str(value)} for value in (4, 5, 6)]
    rows += [{"g": "C", "m": str(value)} for value in (7, 8, 9)]
    rows += [{"g": "C", "m": ""}, {"g": "", "m": "3"}]

    result, groups = compare_groups(rows, "g", "m")

    assert result["test"] == "Kruskal-Wallis"
    assert result["n"] == 9
    assert result["n_missing"] == 2
    assert result["effect_value"] == pytest.approx(result["statistic"] / 8)
    assert [item["group"] for item in groups] == ["A", "B", "C"]


def test_compare_groups_uses_mann_whitney_with_two_groups() -> None:
    rows = [{"g": "A", "m": str(value)} for value in (1, 2, 3)] + [{"g": "B", "m": str(value)} for value in (4, 5, 6)]

    result, _ = compare_groups(rows, "g", "m")

    assert result["test"] == "Mann-Whitney"
    assert result["effect_size"] == "cliffs_delta"
    assert result["effect_value"] == pytest.approx(-1.0)


def test_metadata_helpers() -> None:
    link = '<https://api.github.com/repositories/1/contributors?per_page=1&anon=true&page=2>; rel="next", <https://api.github.com/repositories/1/contributors?per_page=1&anon=true&page=57>; rel="last"'

    assert contributor_count([{}], link) == 57
    assert contributor_count([{}], "") == 1
    assert contributor_count([], "") == 0
    assert age_in_years("2024-12-31T00:00:00Z") == pytest.approx(365 / 365.25)


def _synthetic_rows(count: int = 40) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    metrics, metadata = [], []
    languages = ["Python", "Go"]
    for index in range(count):
        repository = f"octo/r{index}"
        metrics.append(
            {
                "repository": repository,
                "deployment_frequency_per_week": str(0.1 + index / 100),
                "lead_time_by_release_days": str(1 + index),
                "lead_time_by_commit_days": str(0.5 + index),
                "cfr_ci": str((index % 10) / 10),
                "cfr_b": "" if index == 0 else str((index % 5) / 5),
                "recovery_median_hours": str(10 + index),
            }
        )
        metadata.append(
            {
                "repository": repository,
                "language": languages[index % 2] if index < 36 else "Ruby",
                "stars": str(1000 + index * 10),
                "contributors": str(5 + index),
                "age_years": str(1 + index / 10),
            }
        )
    return metrics, metadata


def test_analyze_runs_holm_over_all_factor_metric_pairs() -> None:
    metrics, metadata = _synthetic_rows()
    rows = [{**metric, **meta} for metric, meta in zip(metrics, metadata)]

    result = analyze(rows)

    assert len(result["tests"]) == 24
    assert all(item["p_holm"] is None or item["p_holm"] >= item["p_value"] for item in result["tests"])
    language_sizes = {item["group"]: item["repositories"] for item in result["group_sizes"] if item["factor"] == "language"}
    assert language_sizes == {"Outras": 40}
    star_tests = [item for item in result["tests"] if item["factor"] == "stars_quartile"]
    assert all(item["test"] == "Kruskal-Wallis" for item in star_tests)
    frequency = next(item for item in star_tests if item["metric"] == "deployment_frequency_per_week")
    assert frequency["extreme_cliffs_delta"] == pytest.approx(1.0)


def test_cli_writes_tables_and_valid_figures(tmp_path) -> None:
    metrics, metadata = _synthetic_rows()
    metrics_path, metadata_path = tmp_path / "metrics.csv", tmp_path / "metadata.csv"
    for path, rows in ((metrics_path, metrics), (metadata_path, metadata)):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    output = tmp_path / "out"

    assert main(["--metrics", str(metrics_path), "--metadata", str(metadata_path), "--output", str(output)]) == 0

    summary = json.loads((output / "rq06-summary.json").read_text(encoding="utf-8"))
    assert summary["repository_count"] == 40
    for name in ("rq06-tests.csv", "rq06-groups.csv", "rq06-group-sizes.csv", "rq06-summary.md"):
        assert (output / name).exists()
    for name in ("rq06-effect-sizes.svg", "rq06-language.svg", "rq06-stars-quartile.svg", "rq06-contributors-quartile.svg", "rq06-age-quartile.svg"):
        ElementTree.parse(output / name)
