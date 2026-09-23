from pathlib import Path

import pytest

from lab02.validate_dashboard import (
    DashboardArtifactError,
    validate_dashboard_artifacts,
)


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DESIGN = ROOT / "data" / "design" / "counterbalancing.csv"


def test_versioned_dashboard_artifacts_are_valid() -> None:
    validate_dashboard_artifacts(REPORTS, DESIGN)


def test_validation_rejects_missing_figure(tmp_path: Path) -> None:
    (tmp_path / "figures").mkdir()
    (tmp_path / "dashboard-trials.csv").write_bytes(
        (REPORTS / "dashboard-trials.csv").read_bytes()
    )

    with pytest.raises(DashboardArtifactError, match="figura ausente"):
        validate_dashboard_artifacts(tmp_path, DESIGN)


def test_validation_rejects_incomplete_table(tmp_path: Path) -> None:
    (tmp_path / "figures").mkdir()
    source = (REPORTS / "dashboard-trials.csv").read_text(encoding="utf-8")
    (tmp_path / "dashboard-trials.csv").write_text(
        "\n".join(source.splitlines()[:-1]) + "\n", encoding="utf-8"
    )

    with pytest.raises(DashboardArtifactError, match="18 trial_id"):
        validate_dashboard_artifacts(tmp_path, DESIGN)