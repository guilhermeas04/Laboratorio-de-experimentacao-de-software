"""CLI do smoke test do ambiente experimental."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .environment_check import EnvironmentChecker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida o ambiente experimental do LAB02 antes dos trials reais."
    )
    parser.add_argument(
        "--demo-dir",
        type=Path,
        help="diretório para saídas de demonstração (padrão: LAB2/data/demo)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checker = EnvironmentChecker(demo_dir=args.demo_dir)
    report = checker.run()

    print("SMOKE TEST DO AMBIENTE LAB02")
    for check in report.checks:
        mark = "OK" if check.ok else "FALHA"
        print(f"[{mark}] {check.name}: {check.detail}")

    if report.demo_trial_path is not None:
        print(f"DEMO trial: {report.demo_trial_path}")
    if report.demo_metrics_path is not None:
        print(f"DEMO métricas: {report.demo_metrics_path}")

    if report.ok:
        print("RESULTADO: ambiente pronto para trials")
        return 0

    print("RESULTADO: ambiente incompleto; corrija as falhas acima antes dos trials reais")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
