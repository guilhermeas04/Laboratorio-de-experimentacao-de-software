"""Testes estatisticos do par P1: Welch e Mann-Whitney."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class TestResult:
    test_name: str
    statistic: float
    p_value: float
    effect_size: float
    effect_size_name: str
    alternative: str
    alpha: float
    reject_null: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def cohens_d(sample_a: np.ndarray, sample_b: np.ndarray) -> float:
    a = np.asarray(sample_a, dtype=float)
    b = np.asarray(sample_b, dtype=float)
    var_a = np.var(a, ddof=1)
    var_b = np.var(b, ddof=1)
    pooled = np.sqrt((var_a + var_b) / 2.0)
    if pooled == 0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / pooled)


def rank_biserial(sample_a: np.ndarray, sample_b: np.ndarray) -> float:
    a = np.asarray(sample_a, dtype=float)
    b = np.asarray(sample_b, dtype=float)
    u = stats.mannwhitneyu(a, b, alternative="two-sided").statistic
    return float(1.0 - (2.0 * u) / (len(a) * len(b)))


def welch_t_test(
    sample_a: np.ndarray,
    sample_b: np.ndarray,
    *,
    alternative: str = "two-sided",
    alpha: float = 0.05,
) -> TestResult:
    result = stats.ttest_ind(sample_a, sample_b, equal_var=False, alternative=alternative)
    p_value = float(result.pvalue)
    return TestResult(
        test_name="welch_t",
        statistic=float(result.statistic),
        p_value=p_value,
        effect_size=cohens_d(sample_a, sample_b),
        effect_size_name="cohens_d",
        alternative=alternative,
        alpha=alpha,
        reject_null=p_value < alpha,
    )


def mann_whitney_test(
    sample_a: np.ndarray,
    sample_b: np.ndarray,
    *,
    alternative: str = "two-sided",
    alpha: float = 0.05,
) -> TestResult:
    result = stats.mannwhitneyu(sample_a, sample_b, alternative=alternative)
    p_value = float(result.pvalue)
    return TestResult(
        test_name="mann_whitney",
        statistic=float(result.statistic),
        p_value=p_value,
        effect_size=rank_biserial(sample_a, sample_b),
        effect_size_name="rank_biserial",
        alternative=alternative,
        alpha=alpha,
        reject_null=p_value < alpha,
    )


def run_both_tests(
    sample_a: np.ndarray,
    sample_b: np.ndarray,
    *,
    alternative: str = "two-sided",
    alpha: float = 0.05,
) -> list[TestResult]:
    return [
        welch_t_test(sample_a, sample_b, alternative=alternative, alpha=alpha),
        mann_whitney_test(sample_a, sample_b, alternative=alternative, alpha=alpha),
    ]
