"""CLI for deterministic acceptance execution outside participant trials."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .kata_catalog import KATAS, KATAS_BY_ID
from .kata_contract import load_solver, run_definition


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Executa os testes congelados dos seis katas")
    parser.add_argument("solution", type=Path, help="arquivo Python que exporta solve(value)")
    parser.add_argument("--kata-id", choices=tuple(kata.kata_id for kata in KATAS))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        solver = load_solver(args.solution)
        definitions = (KATAS_BY_ID[args.kata_id],) if args.kata_id else KATAS
        results = [
            (definition, run_definition(definition, solver))
            for definition in definitions
        ]
    except (OSError, ValueError, SyntaxError) as error:
        print(f"ERRO: {error}")
        return 2

    total = sum(len(cases) for _, cases in results)
    passing = sum(sum(passed for _, passed, _ in cases) for _, cases in results)
    failing = total - passing
    print(f"total={total} passing={passing} failing={failing}")
    for definition, cases in results:
        for name, passed, message in cases:
            status = "PASS" if passed else "FAIL"
            print(f"{status} {definition.kata_id}/{name}: {message}")
    return 0 if failing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
