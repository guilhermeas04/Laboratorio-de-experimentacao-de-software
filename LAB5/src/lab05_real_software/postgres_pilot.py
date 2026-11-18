"""Run the LAB05 PostgreSQL pilot against disposable local containers."""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

from .collector import PilotCollector
from .config_loader import load_study_config
from .validator import validate_raw_directory

import json


LAB_ROOT = Path(__file__).resolve().parents[2]
VERSIONS = ("15.20", "17.12")
DATASET = """
CREATE TABLE orders AS
SELECT id, id % 1000 AS customer_id, id % 10000 AS amount
FROM generate_series(1, 100000) AS series(id);
CREATE INDEX ON orders (customer_id);
ANALYZE orders;
"""
QUERY = """
SELECT sum(amount) FROM orders WHERE customer_id = 42;
"""
MEASUREMENT = f"""
SELECT current_setting('server_version');
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {QUERY}
"""


def docker(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["docker", *args], check=True, text=True, stdout=subprocess.PIPE if capture else None
    )
    return result.stdout.strip() if capture else ""


def wait_until_ready(container: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["docker", "exec", container, "pg_isready", "-q", "-h", "127.0.0.1", "-U", "postgres"],
            check=False, capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError("PostgreSQL did not become ready within 60 seconds")


def run_round(collector: PilotCollector, version: str, repetition: int) -> bool:
    container = docker(
        "run", "--detach", "--rm", "--pull=never", "--network=none",
        "--cpus=1", "--memory=512m", "--shm-size=128m", "--tmpfs",
        "/var/lib/postgresql/data:rw,size=256m", "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
        f"postgres:{version}", capture=True,
    )
    try:
        wait_until_ready(container)
        psql = (
            "docker", "exec", container, "psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1",
            "-U", "postgres", "-d", "postgres",
        )
        subprocess.run([*psql, "-c", DATASET, "-c", QUERY], check=True, timeout=60)
        record = collector.collect_local(
            [*psql, "-c", MEASUREMENT], software_version=version, repetition=repetition
        )
        return record["status"] == "success"
    finally:
        docker("rm", "-f", container, capture=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=LAB_ROOT / "data" / "raw")
    parser.add_argument("--blocks", type=int, default=2)
    args = parser.parse_args()
    if args.blocks < 1:
        parser.error("--blocks must be at least 1")

    study = load_study_config(LAB_ROOT / "config" / "study.json")
    ethics = json.loads((LAB_ROOT / "config" / "ethics.json").read_text(encoding="utf-8"))
    collector = PilotCollector(args.raw_dir, ethics, study)
    failures = 0
    for block in range(1, args.blocks + 1):
        versions = VERSIONS if block % 2 == 1 else reversed(VERSIONS)
        for version in versions:
            failures += not run_round(collector, version, block)
    validate_raw_directory(args.raw_dir)
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
