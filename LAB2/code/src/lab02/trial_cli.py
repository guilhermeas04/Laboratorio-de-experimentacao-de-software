"""Interface de linha de comando do cronômetro de trials."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .trial_timer import DEFAULT_OUTPUT_DIR, DEFAULT_SESSIONS_DIR, TrialTimer, TrialTimerError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cronômetro e coletor de trials do LAB02")
    parser.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="inicia um trial")
    start.add_argument("--trial-id", required=True)
    start.add_argument("--participant", required=True)
    start.add_argument("--kata-id", required=True)
    start.add_argument("--treatment", required=True, choices=("with_ai", "manual"))
    start.add_argument("--execution-order", required=True, type=int)
    start.add_argument("--assistant-name")
    start.add_argument("--assistant-version")

    status = subparsers.add_parser("status", help="consulta o tempo de um trial")
    status.add_argument("--trial-id", required=True)

    finish = subparsers.add_parser("finish", help="encerra e registra um trial")
    finish.add_argument("--trial-id", required=True)
    finish.add_argument("--tests-total", required=True, type=int)
    finish.add_argument("--tests-passing", required=True, type=int)
    finish.add_argument("--prompt-count", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    timer = TrialTimer(sessions_dir=args.sessions_dir, output_dir=args.output_dir)
    try:
        if args.command == "start":
            session = timer.start(
                trial_id=args.trial_id,
                participant=args.participant,
                kata_id=args.kata_id,
                treatment=args.treatment,
                execution_order=args.execution_order,
                assistant_name=args.assistant_name,
                assistant_version=args.assistant_version,
            )
            print(f"INICIADO: {session.trial_id} às {session.started_at}")
        elif args.command == "status":
            status = timer.status(args.trial_id)
            print(
                f"STATUS: {status.trial_id} | decorrido={status.elapsed_seconds:.1f}s "
                f"| restante={status.remaining_seconds:.1f}s | limite={status.time_box_reached}"
            )
        else:
            record, output_path = timer.finish(
                args.trial_id,
                tests_total=args.tests_total,
                tests_passing=args.tests_passing,
                prompt_count=args.prompt_count,
            )
            result = "CENSURADO" if record.censored else "CONCLUÍDO"
            print(
                f"{result}: {record.trial_id} | tempo={record.elapsed_seconds:.1f}s "
                f"| sucesso={record.success_rate:.2f}% | arquivo={output_path}"
            )
    except TrialTimerError as error:
        print(f"ERRO: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
