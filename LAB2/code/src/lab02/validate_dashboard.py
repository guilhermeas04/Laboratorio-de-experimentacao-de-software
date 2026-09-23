"""Validate versioned LAB02 dashboard artifacts."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Sequence

import matplotlib.image as image

from .rq12_analysis import DEFAULT_DESIGN, read_design


LAB2_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPORTS_DIR = LAB2_ROOT / "reports"
FIGURE_NAMES = (
    "dashboard-rq1-time.png",
    "dashboard-rq2-outcomes.png",
    "dashboard-rq3-static-metrics.png",
)
MINIMUM_FILE_SIZE = 10_000
MINIMUM_WIDTH = 640
MINIMUM_HEIGHT = 400


class DashboardArtifactError(RuntimeError):
    """Raised when a dashboard artifact is missing or invalid."""


def validate_dashboard_artifacts(
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    design_path: Path = DEFAULT_DESIGN,
) -> None:
    """Validate figures and the consolidated table used by the dashboard."""

    expected_trial_ids = {assignment.trial_id for assignment in read_design(design_path)}
    if len(expected_trial_ids) != 18:
        raise DashboardArtifactError(
            f"o desenho oficial deve conter 18 trials, encontrou {len(expected_trial_ids)}"
        )

    table_path = reports_dir / "dashboard-trials.csv"
    if not table_path.is_file() or table_path.stat().st_size == 0:
        raise DashboardArtifactError(f"tabela ausente ou vazia: {table_path}")
    try:
        with table_path.open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
    except (OSError, UnicodeError, csv.Error) as error:
        raise DashboardArtifactError(f"tabela invalida: {table_path}: {error}") from error

    trial_ids = [row.get("trial_id", "") for row in rows]
    if len(rows) != 18 or set(trial_ids) != expected_trial_ids or len(set(trial_ids)) != 18:
        raise DashboardArtifactError(
            "dashboard-trials.csv deve conter exatamente os 18 trial_id oficiais"
        )
    required_columns = {"trial_id", "treatment", "elapsed_seconds", "success_rate"}
    if not required_columns.issubset(rows[0]):
        missing = sorted(required_columns - set(rows[0]))
        raise DashboardArtifactError(f"colunas ausentes na tabela: {', '.join(missing)}")

    for figure_name in FIGURE_NAMES:
        figure_path = reports_dir / "figures" / figure_name
        _validate_png(figure_path)


def _validate_png(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < MINIMUM_FILE_SIZE:
        raise DashboardArtifactError(
            f"figura ausente, vazia ou menor que {MINIMUM_FILE_SIZE} bytes: {path}"
        )
    try:
        with path.open("rb") as file:
            if file.read(8) != b"\x89PNG\r\n\x1a\n":
                raise DashboardArtifactError(f"formato invalido, esperado PNG: {path}")
        pixels = image.imread(path)
    except (OSError, ValueError) as error:
        raise DashboardArtifactError(f"figura invalida: {path}: {error}") from error

    if pixels.ndim < 2 or pixels.shape[1] < MINIMUM_WIDTH or pixels.shape[0] < MINIMUM_HEIGHT:
        raise DashboardArtifactError(
            f"dimensoes insuficientes em {path}: {pixels.shape[1]}x{pixels.shape[0]}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida os artefatos visuais do dashboard LAB02.")
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_dashboard_artifacts(args.reports_dir, args.design)
    except (DashboardArtifactError, OSError, ValueError) as error:
        print(f"ERRO: {error}")
        return 1
    print("Artefatos do dashboard validos: 18 trials e 3 figuras PNG")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())