"""Infraestrutura compartilhada do experimento LAB02."""

from .trial_record import MAX_TRIAL_SECONDS, TrialRecord, TrialValidationError
from .trial_timer import TrialSession, TrialStatus, TrialTimer, TrialTimerError

__all__ = [
    "MAX_TRIAL_SECONDS",
    "TrialRecord",
    "TrialSession",
    "TrialStatus",
    "TrialTimer",
    "TrialTimerError",
    "TrialValidationError",
]
