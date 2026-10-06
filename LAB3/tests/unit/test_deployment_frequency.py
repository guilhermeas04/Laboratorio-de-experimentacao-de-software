from datetime import date

import pytest

from lab03_dora.metrics.deployment_frequency import deployment_frequency, observation_weeks


def test_observation_window_of_2025_has_about_52_weeks() -> None:
    weeks = observation_weeks(date(2025, 1, 1), date(2025, 12, 31))

    assert weeks == pytest.approx(365 / 7)
    assert round(weeks, 1) == 52.1


def test_deployment_frequency_divides_releases_by_weeks() -> None:
    start = date(2025, 1, 1)
    end = date(2025, 12, 31)

    frequency = deployment_frequency(10, start, end)

    assert frequency == pytest.approx(10 / (365 / 7))


def test_repository_without_releases_has_frequency_zero() -> None:
    assert deployment_frequency(0, date(2025, 1, 1), date(2025, 1, 7)) == 0


def test_negative_release_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        deployment_frequency(-1, date(2025, 1, 1), date(2025, 1, 7))


def test_inverted_window_is_rejected() -> None:
    with pytest.raises(ValueError):
        deployment_frequency(1, date(2025, 12, 31), date(2025, 1, 1))
