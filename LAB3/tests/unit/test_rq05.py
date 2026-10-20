import csv
import json
from xml.etree import ElementTree

import pytest

from lab03_dora.analysis.rq05 import analyze, main, paired_values, spearman, strength_label


def _rows():
    return [
        {"repository": "a/1", "deployment_frequency_per_week": "0.1", "cfr_ci": "0.9", "cfr_b": "0.0"},
        {"repository": "a/2", "deployment_frequency_per_week": "0.2", "cfr_ci": "0.7", "cfr_b": "0.1"},
        {"repository": "a/3", "deployment_frequency_per_week": "0.4", "cfr_ci": "0.5", "cfr_b": ""},
        {"repository": "a/4", "deployment_frequency_per_week": "0.8", "cfr_ci": "0.3", "cfr_b": "0.3"},
        {"repository": "a/5", "deployment_frequency_per_week": "1.6", "cfr_ci": "0.1", "cfr_b": "0.4"},
    ]


def test_missing_pair_is_excluded_not_zero() -> None:
    xs, ys, missing = paired_values(_rows(), "deployment_frequency_per_week", "cfr_b")

    assert len(xs) == 4
    assert 0.0 in ys
    assert missing == [{"repository": "a/3", "missing_columns": "cfr_b"}]


def test_spearman_perfect_monotonic_relations() -> None:
    rho, p_value, low, high, note = spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50], resamples=200)

    assert rho == pytest.approx(1.0)
    assert p_value < 0.05
    assert note == ""
    assert low is not None and high is not None
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1], resamples=0)[0] == pytest.approx(-1.0)


def test_spearman_matches_known_value_with_ties() -> None:
    rho, *_ = spearman([1, 2, 2, 3, 4], [2, 1, 3, 3, 5], resamples=0)

    # Postos medios: x = 1, 2.5, 2.5, 4, 5; y = 2, 1, 3.5, 3.5, 5.
    assert rho == pytest.approx(7.25 / 9.5)


def test_spearman_refuses_degenerate_input() -> None:
    assert spearman([1, 2], [3, 4])[4] == "menos de 3 pares completos"
    assert spearman([1, 1, 1], [1, 2, 3])[0] is None


def test_strength_bands() -> None:
    assert strength_label(None) == "indefinida"
    assert strength_label(0.05) == "desprezivel"
    assert strength_label(-0.2) == "fraca"
    assert strength_label(0.45) == "moderada"
    assert strength_label(-0.5) == "forte"


def test_analyze_reports_each_variant_separately() -> None:
    result = analyze(_rows())
    by_variant = {item["variant"]: item for item in result["correlations"]}

    assert by_variant["cfr_a"]["n_used"] == 5
    assert by_variant["cfr_a"]["rho"] == pytest.approx(-1.0)
    assert by_variant["cfr_b"]["n_used"] == 4
    assert by_variant["cfr_b"]["n_missing"] == 1
    assert by_variant["cfr_b"]["rho"] == pytest.approx(1.0)


def test_cli_writes_tables_and_figures(tmp_path) -> None:
    dataset = tmp_path / "metrics.csv"
    with dataset.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(_rows()[0]))
        writer.writeheader()
        writer.writerows(_rows())
    output = tmp_path / "out"

    assert main(["--input", str(dataset), "--output", str(output)]) == 0

    summary = json.loads((output / "rq05-summary.json").read_text(encoding="utf-8"))
    assert [item["variant"] for item in summary["correlations"]] == ["cfr_a", "cfr_b"]
    assert "series" not in summary
    assert (output / "rq05-spearman.csv").exists()
    assert (output / "rq05-missing.csv").read_text(encoding="utf-8").count("a/3") == 1
    figure = (output / "rq05-frequency-vs-cfr-a.svg").read_text(encoding="utf-8")
    assert figure.count("<circle") == 5
    ElementTree.fromstring(figure)
    assert (output / "rq05-frequency-vs-cfr-b.svg").read_text(encoding="utf-8").count("<circle") == 4
