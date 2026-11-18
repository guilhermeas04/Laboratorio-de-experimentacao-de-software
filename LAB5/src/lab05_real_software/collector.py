"""Reproducible local pilot collector for LAB05.

This collector is intentionally local-first. External requests are disabled by
default and are guarded by the ethics configuration and a one-second limiter.
"""

from __future__ import annotations

import argparse
import json
import platform
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class ExternalRequestNotAllowed(RuntimeError):
    """Raised when a request violates the configured study protocol."""


class ExternalRequestLimiter:
    """Enforce at most one external request per configured second."""

    def __init__(
        self,
        ethics_config: dict,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        external = ethics_config.get("external_requests", {})
        if not isinstance(external, dict):
            raise ValueError("external_requests must be an object")

        self.allowed = external.get("allowed") is True
        max_per_second = external.get("max_per_second", 0)
        if not isinstance(max_per_second, (int, float)):
            raise ValueError("external_requests.max_per_second must be numeric")
        self.max_per_second = float(max_per_second)
        self.interval = 1.0 / self.max_per_second if self.max_per_second > 0 else None
        self._clock = clock
        self._sleeper = sleeper
        self._last_request: float | None = None
        self._lock = threading.Lock()

    def wait(self) -> None:
        if not self.allowed:
            raise ExternalRequestNotAllowed(
                "External requests are prohibited by LAB5/config/ethics.json"
            )
        if self.interval is None or self.interval < 1.0:
            raise ExternalRequestNotAllowed(
                "Protocol permits no more than one external request per second"
            )

        with self._lock:
            now = self._clock()
            if self._last_request is not None:
                remaining = self.interval - (now - self._last_request)
                if remaining > 0:
                    self._sleeper(remaining)
                    now = self._clock()
            self._last_request = now


class PilotCollector:
    """Collect one or more local command executions and preserve raw metadata."""

    def __init__(
        self,
        raw_dir: str | Path,
        ethics_config: dict,
        study_config: dict | None = None,
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.ethics_config = ethics_config
        self.study_config = study_config or {}
        self.limiter = ExternalRequestLimiter(ethics_config)

    def collect_local(
        self,
        command: Iterable[str],
        *,
        software_version: str,
        repetition: int,
        timeout_seconds: float = 30.0,
        cwd: str | Path | None = None,
    ) -> dict:
        """Run a local command once and atomically write its raw JSON record."""
        argv = [str(part) for part in command]
        if not argv:
            raise ValueError("command cannot be empty")

        started_at = utc_now()
        start = time.perf_counter()
        error: str | None = None
        returncode: int | None = None
        stdout = ""
        stderr = ""

        try:
            completed = subprocess.run(
                argv,
                cwd=None if cwd is None else str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            status = "success" if completed.returncode == 0 else "error"
            if completed.returncode != 0:
                error = f"command exited with status {completed.returncode}"
        except subprocess.TimeoutExpired as exc:
            status = "error"
            error = f"command timed out after {timeout_seconds:g} seconds"
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else str(exc)
        except (OSError, ValueError) as exc:
            status = "error"
            error = f"{type(exc).__name__}: {exc}"

        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        ended_at = utc_now()

        software = self.study_config.get("software", {})
        software_name = software.get("name") if isinstance(software, dict) else None
        record = {
            "schema_version": "lab05-pilot-v1",
            "collected_at": started_at,
            "ended_at": ended_at,
            "status": status,
            "error": error,
            "software": software_name,
            "software_version": software_version,
            "repetition": repetition,
            "command": argv,
            "returncode": returncode,
            "duration_ms": duration_ms,
            "stdout": stdout[-10000:],
            "stderr": stderr[-10000:],
            "metadata": {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "execution_mode": "local",
                "timeout_seconds": timeout_seconds,
                "cwd": str(Path.cwd() if cwd is None else cwd),
            },
        }

        filename = (
            f"pilot-{software_version}-r{repetition:03d}-"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
        )
        path = self.raw_dir / filename
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
        return record

    def fetch_external(self, url: str, opener: Callable[..., object], timeout: float = 10.0) -> dict:
        """Perform a rate-limited external request if explicitly allowed."""
        if self.ethics_config.get("external_requests", {}).get("load_testing_third_party_systems"):
            raise ExternalRequestNotAllowed("Third-party load testing is prohibited")

        self.limiter.wait()
        try:
            response = opener(url, timeout=timeout)
            return {"status": "success", "url": url, "response": response}
        except Exception as exc:
            return {
                "status": "error",
                "url": url,
                "error": f"{type(exc).__name__}: {exc}",
            }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LAB05 local pilot collector")
    parser.add_argument("--raw-dir", type=Path, default=Path(__file__).parents[2] / "data" / "raw")
    parser.add_argument("--study-config", type=Path, default=Path(__file__).parents[2] / "config" / "study.json")
    parser.add_argument("--ethics-config", type=Path, default=Path(__file__).parents[2] / "config" / "ethics.json")
    parser.add_argument("--software-version", default="pilot")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be at least 1")

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("Provide a local command after --")

    study_config = json.loads(args.study_config.read_text(encoding="utf-8"))
    ethics_config = json.loads(args.ethics_config.read_text(encoding="utf-8"))
    collector = PilotCollector(args.raw_dir, ethics_config, study_config)

    success_count = 0
    for repetition in range(1, args.repetitions + 1):
        record = collector.collect_local(
            command,
            software_version=args.software_version,
            repetition=repetition,
            timeout_seconds=args.timeout,
        )
        if record["status"] == "success":
            success_count += 1

    print(json.dumps({"repetitions": args.repetitions, "successes": success_count}, indent=2))
    return 0 if success_count == args.repetitions else 1


if __name__ == "__main__":
    raise SystemExit(main())
