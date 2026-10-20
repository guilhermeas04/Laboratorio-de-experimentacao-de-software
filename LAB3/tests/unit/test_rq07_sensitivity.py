import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from rq07_sensitivity import classify, weighted_kappa


def test_classify_dora_cutoffs():
    assert classify(7.0, (0.23, 1.0, 7.0)) == "Elite"
    assert classify(0.5, (0.23, 1.0, 7.0)) == "Medium"
    assert classify(2.0, (1.0, 7.0, 30.0), reverse=True) == "High"


def test_weighted_kappa_perfect_and_disagreement():
    assert weighted_kappa(["Elite", "Low"], ["Elite", "Low"]) == 1.0
    assert weighted_kappa(["Elite", "Low"], ["Low", "Elite"]) < 0
