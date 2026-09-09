"""Infraestrutura compartilhada do experimento LAB02."""

from .environment_check import EnvironmentChecker, SmokeReport
from .static_metrics import StaticMetricsError, StaticMetricsResult, analyze_trial_source
from .trial_record import MAX_TRIAL_SECONDS, TrialRecord, TrialValidationError
from .trial_timer import TrialSession, TrialStatus, TrialTimer, TrialTimerError

__all__ = [
    "MAX_TRIAL_SECONDS",
    "EnvironmentChecker",
    "SmokeReport",
    "StaticMetricsError",
    "StaticMetricsResult",
    "TrialRecord",
    "TrialSession",
    "TrialStatus",
    "TrialTimer",
    "TrialTimerError",
    "TrialValidationError",
    "analyze_trial_source",
]
