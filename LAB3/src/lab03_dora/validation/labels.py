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


def binary_confusion_matrix(
    expected: Iterable[str], predicted: Iterable[str], *, positive: str = "corretiva"
) -> dict[str, int]:
    """Calcula TN, FP, FN e TP para rótulos binários."""

    expected_values = list(expected)
    predicted_values = list(predicted)
    if len(expected_values) != len(predicted_values):
        raise ValueError("expected e predicted devem ter o mesmo tamanho")
    return {
        "true_negative": sum(actual != positive and guess != positive for actual, guess in zip(expected_values, predicted_values)),
        "false_positive": sum(actual != positive and guess == positive for actual, guess in zip(expected_values, predicted_values)),
        "false_negative": sum(actual == positive and guess != positive for actual, guess in zip(expected_values, predicted_values)),
        "true_positive": sum(actual == positive and guess == positive for actual, guess in zip(expected_values, predicted_values)),
    }


def validate_gold_standard(
    gold_rows: Iterable[Mapping[str, str]],
    predictions: Iterable[Mapping[str, str]],
) -> dict[str, object]:
    """Compara previsoes com o consenso, separando sem_release e ausencias."""

    prediction_by_key = {
        (str(row.get("repository") or ""), str(row.get("release_id") or "")): row.get("prediction", "")
        for row in predictions
    }
    rows = list(gold_rows)
    evaluable = [row for row in rows if row.get("consensus_label") != NON_EVALUABLE_LABEL]
    matched = [
        row for row in evaluable
        if (str(row.get("repository") or ""), str(row.get("release_id") or "")) in prediction_by_key
    ]
    expected = [str(row.get("consensus_label") or "") for row in matched]
    predicted = [
        str(prediction_by_key[(str(row.get("repository") or ""), str(row.get("release_id") or ""))])
        for row in matched
    ]
    metrics = binary_precision_recall_f1(expected, predicted)
    return {
        **metrics,
        "sample_size": len(rows),
        "evaluable_count": len(evaluable),
        "matched_count": len(matched),
        "excluded_non_evaluable_count": len(rows) - len(evaluable),
        "missing_prediction_count": len(evaluable) - len(matched),
        "coverage": len(matched) / len(evaluable) if evaluable else 0.0,
        "confusion_matrix": binary_confusion_matrix(expected, predicted),
    }
