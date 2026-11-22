"""Run or resume the full LAB05S02 PostgreSQL collection."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
from tempfile import gettempdir

from .postgres_collection import CONFIG, LAB_ROOT, block_orders, docker, run_round


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_manifest(path: Path, manifest: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


@contextmanager
def campaign_lock(destination: Path):
    """Release the lock automatically if the collector exits unexpectedly."""
    key = sha256(str(destination.resolve()).encode()).hexdigest()
    with (Path(gettempdir()) / f"lab05s02-{key}.lock").open("a+b") as lock:
        try:
            if platform.system() == "Windows":
                import msvcrt

                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("this campaign is already running") from exc
        yield


def environment_snapshot(config: dict) -> dict:
    fields = ("ID", "ServerVersion", "OSType", "Architecture", "CgroupVersion", "NCPU", "MemTotal")
    template = "|".join("{{." + field + "}}" for field in fields)
    environment = dict(zip(fields, docker("info", "--format", template).split("|"), strict=True))
    daemon_id = environment.pop("ID")
    environment["daemon_fingerprint"] = sha256(daemon_id.encode()).hexdigest()
    environment["collector_platform"] = platform.system()
    environment["images"] = {
        version: docker("image", "inspect", "--format", "{{.Id}}", f"postgres:{version}")
        for version in config["versions"]
    }
    return environment


def plan_rounds(config: dict) -> list[dict]:
    return [
        {"block": block, "position": position, "software_version": version, "scenario": scenario}
        for block, versions in enumerate(block_orders(config), 1)
        for position, version in enumerate(versions, 1)
        for scenario in config["queries"]
    ]


def reconcile(destination: Path, manifest: dict) -> dict:
    """Reconcile each attempt with the immutable files actually on disk."""
    planned = manifest["planned_rounds"]
    accepted = set()
    counts = {"planned": len(planned), "recorded": 0, "successful": 0, "failed": 0}
    for attempt in manifest["attempts"]:
        block = attempt["block"]
        expected = [item for item in planned if item["block"] == block]
        files = []
        for item in expected:
            slot = f"b{block:03d}-p{item['position']}-{item['scenario']}"
            relative = Path("rounds") / f"{attempt['execution_id']}-{slot}.json"
            path = destination / relative
            if not path.exists():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            if (
                any(record.get(key) != value for key, value in item.items())
                or record.get("campaign_id") != manifest["campaign_id"]
                or record.get("execution_id") != attempt["execution_id"]
                or record.get("round_id") != path.stem
                or record.get("configuration") != manifest["configuration"]
                or record.get("status") not in {"success", "error"}
            ):
                raise ValueError(f"round metadata mismatch: {relative.as_posix()}")
            entry = {"file": relative.as_posix(), "status": record["status"]}
            if record["status"] == "error":
                entry["reason"] = record.get("error") or record.get("cleanup_error") or "round failed"
            elif record.get("image_id") != manifest["environment"]["images"][item["software_version"]]:
                entry["status"] = "error"
                entry["reason"] = "PostgreSQL image changed during collection"
            files.append(entry)
            counts["recorded"] += 1
            counts["successful" if entry["status"] == "success" else "failed"] += 1
        attempt["records"] = files
        qualifies = (attempt.get("ended_at") is not None and len(files) == len(expected)
                     and all(entry["status"] == "success" for entry in files))
        if qualifies and "deviation" not in attempt:
            if block in accepted:
                raise ValueError(f"multiple accepted attempts for block {block}")
            attempt["status"] = "accepted"
            accepted.add(block)
        elif attempt["status"] == "accepted":
            raise ValueError(f"accepted block {block} changed on disk")
        elif attempt["status"] == "interrupted":
            pass
        elif any(entry["status"] == "error" for entry in files) or "deviation" in attempt:
            attempt["status"] = "failed"
        else:
            attempt["status"] = "running"

    tracked = {entry["file"] for attempt in manifest["attempts"] for entry in attempt["records"]}
    actual = {path.relative_to(destination).as_posix() for path in (destination / "rounds").glob("*.json")}
    if actual != tracked:
        raise ValueError("raw directory contains records outside the manifest")
    counts["accepted_blocks"] = len(accepted)
    counts["accepted_rounds"] = sum(item["block"] in accepted for item in planned)
    counts["pending_rounds"] = counts["planned"] - counts["accepted_rounds"]
    manifest["counts"] = counts
    return accepted


def run_campaign(config: dict, destination: Path, campaign_id: str, *, resume: bool) -> int:
    path = destination / "manifest.json"
    if resume != path.is_file():
        raise ValueError("use --resume with an existing manifest or choose a new campaign ID")
    if resume:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (manifest["campaign_id"] != campaign_id or manifest["configuration"] != config
                or manifest["planned_rounds"] != plan_rounds(config)):
            raise ValueError("campaign ID, configuration or planned order has changed")
        accepted = reconcile(destination, manifest)
        if len(accepted) == config["blocks"]:
            print(f"{campaign_id}: already complete", flush=True)
            return 0
        for attempt in manifest["attempts"]:
            if attempt["status"] == "running":
                attempt["status"] = "interrupted"
                attempt["deviation"] = "process interrupted before completing the block"
                attempt["ended_at"] = utc_now()
    else:
        manifest = {
            "schema_version": "lab05-s02-campaign-v1",
            "campaign_id": campaign_id,
            "started_at": utc_now(),
            "configuration": config,
            "environment": environment_snapshot(config),
            "planned_rounds": plan_rounds(config),
            "attempts": [],
            "deviations": [],
        }
        destination.mkdir(parents=True)
        (destination / "rounds").mkdir()
        accepted = set()

    manifest["status"] = "running"
    manifest["ended_at"] = None
    if resume and environment_snapshot(config) == manifest["environment"]:
        orphaned = docker("ps", "-aq", "--filter", f"label=lab05s02.campaign={campaign_id}").splitlines()
        if orphaned:
            docker("rm", "-f", *orphaned)
            manifest["deviations"].append({"at": utc_now(), "reason": "removed containers left by an interrupted attempt",
                                            "containers_removed": len(orphaned)})
    reconcile(destination, manifest)
    write_manifest(path, manifest)
    for block in range(1, config["blocks"] + 1):
        if block in accepted:
            continue
        if environment_snapshot(config) != manifest["environment"]:
            manifest["deviations"].append({"at": utc_now(), "block": block, "reason": "environment changed"})
            break
        attempt_number = 1 + sum(attempt["block"] == block for attempt in manifest["attempts"])
        execution_id = f"{campaign_id}-b{block:03d}-a{attempt_number:02d}"
        attempt = {"execution_id": execution_id, "block": block, "attempt": attempt_number,
                   "started_at": utc_now(), "status": "running", "records": []}
        manifest["attempts"].append(attempt)
        write_manifest(path, manifest)
        try:
            for item in manifest["planned_rounds"]:
                if item["block"] != block:
                    continue
                record = run_round(config, destination / "rounds", block=block,
                                   position=item["position"], version=item["software_version"],
                                   scenario=item["scenario"], execution_id=execution_id,
                                   campaign_id=campaign_id)
                print(f"{record['round_id']} {record['status']}", flush=True)
                expected_image = manifest["environment"]["images"][item["software_version"]]
                if record["status"] != "success" or record["image_id"] != expected_image:
                    break
            if environment_snapshot(config) != manifest["environment"]:
                attempt["deviation"] = "environment changed during the block"
        except KeyboardInterrupt:
            attempt["status"] = "interrupted"
            attempt["deviation"] = "collection interrupted during the block"
        attempt["ended_at"] = utc_now()
        accepted = reconcile(destination, manifest)
        write_manifest(path, manifest)
        if block not in accepted:
            break

    manifest["status"] = "complete" if len(accepted) == config["blocks"] else "incomplete"
    manifest["ended_at"] = utc_now()
    write_manifest(path, manifest)
    print(f"{campaign_id}: {manifest['status']} {manifest['counts']}", flush=True)
    return int(manifest["status"] != "complete")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=LAB_ROOT / "data" / "raw" / "s02")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--resume", action="store_true")
    mode.add_argument("--verify", action="store_true", help="verify completed files without Docker")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", args.campaign_id):
        parser.error("--campaign-id must have 1 to 40 lowercase letters, digits or hyphens")
    destination = args.output_dir / args.campaign_id
    with campaign_lock(destination):
        if args.verify:
            manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
            if manifest["campaign_id"] != args.campaign_id:
                raise ValueError("manifest belongs to another campaign")
            expected = manifest["counts"].copy()
            accepted = reconcile(destination, manifest)
            if expected != manifest["counts"]:
                raise ValueError("stored counts do not match the raw records")
            complete = len(accepted) == manifest["configuration"]["blocks"]
            if (manifest["status"] == "complete") != complete:
                raise ValueError("stored campaign status does not match the accepted rounds")
            print(f"{args.campaign_id}: {manifest['status']} {manifest['counts']}", flush=True)
            return int(not complete)
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        return run_campaign(config, destination, args.campaign_id, resume=args.resume)


if __name__ == "__main__":
    raise SystemExit(main())
