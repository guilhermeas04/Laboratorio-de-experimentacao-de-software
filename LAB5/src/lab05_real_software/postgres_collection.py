"""Configure and measure an isolated PostgreSQL round for LAB05S02."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import random
import re
from statistics import median
import subprocess
import time
from uuid import uuid4

from .postgres_pilot import LAB_ROOT, wait_until_ready


CONFIG = LAB_ROOT / "config" / "collection-s02.json"


def docker(*args: str, script: str | None = None, timeout: int = 30) -> str:
    return subprocess.run(
        ["docker", *args], input=script, text=True, encoding="utf-8",
        errors="replace", capture_output=True, check=True, timeout=timeout,
    ).stdout.strip()


def block_orders(config: dict) -> list[tuple[str, str]]:
    versions = tuple(config["versions"])
    blocks = config["blocks"]
    if len(versions) != 2 or blocks < 2 or blocks % 2:
        raise ValueError("expected two versions and a positive even number of blocks")
    orders = [versions, versions[::-1]] * (blocks // 2)
    random.Random(config["seed"]).shuffle(orders)
    return orders


def sample_resources(container: str, cgroup_version: str) -> dict:
    before = time.monotonic()
    if cgroup_version == "2":
        output = docker("exec", container, "cat", "/sys/fs/cgroup/cpu.stat",
                        "/sys/fs/cgroup/memory.current")
        rows = output.splitlines()
        cpu = dict(row.split() for row in rows[:-1])
        cpu_usage_usec, memory_bytes = int(cpu["usage_usec"]), int(rows[-1])
    else:
        output = docker("exec", container, "cat", "/sys/fs/cgroup/cpuacct/cpuacct.usage",
                        "/sys/fs/cgroup/memory/memory.usage_in_bytes")
        cpu_ns, memory_bytes = map(int, output.splitlines())
        cpu_usage_usec = cpu_ns / 1000
    timestamp = (before + time.monotonic()) / 2
    return {
        "time_monotonic_seconds": timestamp,
        "cpu_usage_usec": cpu_usage_usec,
        "memory_bytes": memory_bytes,
    }


def summarize_load(output: str, samples: list[dict], cpus: int) -> dict:
    processed = re.search(r"^number of transactions actually processed: (\d+)\s*$", output, re.M)
    tps = re.search(r"^tps = ([\d.]+) \(without initial connection time\)", output, re.M)
    latency = re.search(r"^latency average = ([\d.]+) ms", output, re.M)
    failed = re.search(r"^number of failed transactions: (\d+)", output, re.M)
    if failed and int(failed[1]):
        raise ValueError(f"pgbench reported {failed[1]} failed transactions")
    if not (processed and tps and latency) or int(processed[1]) < 1 or len(samples) < 2:
        raise ValueError("pgbench output or resource samples are incomplete")
    first, last = samples[0], samples[-1]
    elapsed = last["time_monotonic_seconds"] - first["time_monotonic_seconds"]
    cpu_used = last["cpu_usage_usec"] - first["cpu_usage_usec"]
    if elapsed <= 0 or cpu_used < 0:
        raise ValueError("invalid resource sampling interval")
    return {
        "queries_completed": int(processed[1]),
        "throughput_queries_per_second": float(tps[1]),
        "client_latency_ms": float(latency[1]),
        "cpu_percent": cpu_used / (elapsed * 1_000_000 * cpus) * 100,
        "memory_mb": sum(sample["memory_bytes"] for sample in samples) / len(samples) / 1_000_000,
        "resource_window_seconds": elapsed,
    }


def benchmark(container: str, query: str, config: dict, duration: int) -> str:
    return docker(
        "exec", "-i", container, "pgbench", "-n", "-U", "postgres",
        "-c", str(config["clients"]), "-j", str(config["jobs"]),
        "-T", str(duration), "-f", "/dev/stdin", "postgres",
        script=query + "\n", timeout=duration + 30,
    )


def measure(container: str, query: str, config: dict, record: dict) -> None:
    psql = ("exec", container, "psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-U", "postgres")
    sql = f"""
    CREATE TABLE orders AS
    SELECT id, (id + {config['seed']}) % 1000 AS customer_id,
           ((id::bigint * 7919 + {config['seed']}) % 10000)::integer AS amount
    FROM generate_series(1, {config['dataset_rows']}) AS series(id);
    ALTER TABLE orders ADD PRIMARY KEY (id);
    CREATE INDEX ON orders (customer_id);
    ANALYZE orders;
    """
    docker(*psql, "-c", sql)
    record["server_version"] = docker(*psql, "-c", "SHOW server_version")
    if record["server_version"].split()[0] != record["software_version"]:
        raise ValueError("server version differs from configured image")
    benchmark(container, query, config, config["warmup_seconds"])
    explain = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
    plans = record["explain"] = [
        json.loads(docker(*psql, "-c", explain))
        for _ in range(config["server_latency_repetitions"])
    ]
    cgroup_version = record["environment"]["cgroup_version"]
    samples = record["resource_samples"] = [sample_resources(container, cgroup_version)]
    with ThreadPoolExecutor(max_workers=1) as executor:
        load = executor.submit(benchmark, container, query, config, config["measurement_seconds"])
        while not load.done():
            time.sleep(config["sample_interval_seconds"])
            if not load.done():
                samples.append(sample_resources(container, cgroup_version))
        record["pgbench_output"] = load.result()
    samples.append(sample_resources(container, cgroup_version))
    record["metrics"] = summarize_load(record["pgbench_output"], samples, config["cpus"])
    record["metrics"]["query_latency_ms"] = median(plan[0]["Execution Time"] for plan in plans)


def run_round(config: dict, destination: Path, *, block: int, position: int,
              version: str, scenario: str, execution_id: str) -> dict:
    round_id = f"{execution_id}-b{block:03d}-p{position}-{scenario}"
    record = {
        "schema_version": "lab05-s02-round-v1",
        "execution_id": execution_id,
        "round_id": round_id,
        "block": block,
        "position": position,
        "software_version": version,
        "scenario": scenario,
        "configuration": config,
        "environment": {"platform": platform.system(), "architecture": platform.machine()},
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": "error",
    }
    container = None
    try:
        image = f"postgres:{version}"
        record["image_id"] = docker("image", "inspect", "--format", "{{.Id}}", image)
        environment = json.loads(docker("info", "--format",
                                        '{"docker":{{json .ServerVersion}},"cgroup_version":{{json .CgroupVersion}}}'))
        if environment["cgroup_version"] not in {"1", "2"}:
            raise ValueError("Docker must expose cgroup v1 or v2")
        record["environment"].update(environment)
        container = docker(
            "run", "--detach", "--rm", "--pull=never", "--network=none",
            f"--cpus={config['cpus']}", f"--memory={config['memory_mb']}m",
            "--shm-size=128m", "--tmpfs", "/var/lib/postgresql/data:rw,size=256m",
            "-e", "POSTGRES_HOST_AUTH_METHOD=trust", image,
            "-c", f"shared_buffers={config['shared_buffers_mb']}MB",
        )
        wait_until_ready(container)
        measure(container, config["queries"][scenario], config, record)
        record["status"] = "success"
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError, KeyError, IndexError) as exc:
        detail = getattr(exc, "stderr", None)
        record["error"] = (detail if isinstance(detail, str) and detail.strip() else str(exc)).strip()
    finally:
        if container:
            try:
                docker("rm", "-f", container)
            except (OSError, subprocess.SubprocessError) as exc:
                record["cleanup_error"] = str(exc)
                record["status"] = "error"
        record["ended_at"] = datetime.now(timezone.utc).isoformat()
        path = destination / f"{round_id}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(path)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Test the S02 instrumentation in both versions")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    execution_id = f"instrumentation-{uuid4().hex[:12]}"
    destination = args.output_dir / execution_id
    destination.mkdir(parents=True)
    records = [
        run_round(config, destination, block=1, position=position, version=version,
                  scenario=scenario, execution_id=execution_id)
        for position, version in enumerate(block_orders(config)[0], 1)
        for scenario in config["queries"]
    ]
    for record in records:
        print(record["round_id"], record["status"], record.get("error", ""))
    print(destination)
    return int(any(record["status"] != "success" for record in records))


if __name__ == "__main__":
    raise SystemExit(main())
