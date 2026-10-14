"""Métricas da validação da heurística de releases corretivas."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

NON_EVALUABLE_LABEL = "sem_release"


def evaluable_labels(rows: Iterable[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """Remove casos sem release antes de comparar rótulos.

    Os casos permanecem nos CSVs brutos para auditoria, mas não possuem uma
    release sobre a qual a heurística possa emitir uma previsão binária.
    """

    return [row for row in rows if row.get("label", "").strip() != NON_EVALUABLE_LABEL]


def binary_precision_recall_f1(
    expected: Iterable[str], predicted: Iterable[str], *, positive: str = "corretiva"
) -> dict[str, float | int]:
    """Calcula precisão, recall e F1 somente para rótulos avaliáveis."""

    expected_values = list(expected)
    predicted_values = list(predicted)
    if len(expected_values) != len(predicted_values):
        raise ValueError("expected e predicted devem ter o mesmo tamanho")
    tp = sum(actual == positive and guess == positive for actual, guess in zip(expected_values, predicted_values))
    fp = sum(actual != positive and guess == positive for actual, guess in zip(expected_values, predicted_values))
    fn = sum(actual == positive and guess != positive for actual, guess in zip(expected_values, predicted_values))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"n": len(expected_values), "true_positive": tp, "false_positive": fp, "false_negative": fn,
            "precision": precision, "recall": recall, "f1": f1}
