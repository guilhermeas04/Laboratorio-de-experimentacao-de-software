"""Interface de linha de comando da pipeline de métricas estáticas."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .static_metrics import (
    STATUS_OK,
    StaticMetricsError,
    analyze_trial_source,
    default_output_path,
    write_metrics_result,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coleta métricas estáticas do código final de um trial (RQ3)."
    )
    parser.add_argument("--trial-id", required=True, help="identificador do trial")
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="arquivo .py ou diretório com o código final do trial",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="caminho do JSON de saída (padrão: data/processed/metrics-<trial-id>.json)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="arquivo TOML de configuração das ferramentas",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        output = args.output or default_output_path(args.trial_id)
        result = analyze_trial_source(
            trial_id=args.trial_id,
            source=args.source,
            config_path=args.config,
        )
        path = write_metrics_result(result, output)
    except StaticMetricsError as error:
        print(f"ERRO: {error}")
        return 1

    metrics = (
        f"loc={result.loc} "
        f"cc_media={result.cyclomatic_complexity_mean} "
        f"cc_max={result.cyclomatic_complexity_max} "
        f"dup={result.duplication_percentage} "
        f"mi={result.maintainability_index}"
    )
    prefix = "OK" if result.status == STATUS_OK else "AVISO"
    print(f"{prefix}: trial={result.trial_id} status={result.status} | {metrics} | arquivo={path}")
    for message in result.messages:
        print(f"- {message}")
    return 0 if result.status == STATUS_OK else 2


if __name__ == "__main__":
    raise SystemExit(main())
