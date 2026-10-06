"""Coletores de dados do GitHub para o LAB03."""

from .workflow_runs import (
    VALID_CONCLUSIONS,
    CollectionResult,
    WorkflowRunClient,
    collect_workflow_runs,
    classify_conclusion,
    month_windows,
    normalize_workflow_run,
)

__all__ = [
    "VALID_CONCLUSIONS",
    "CollectionResult",
    "WorkflowRunClient",
    "collect_workflow_runs",
    "classify_conclusion",
    "month_windows",
    "normalize_workflow_run",
]
