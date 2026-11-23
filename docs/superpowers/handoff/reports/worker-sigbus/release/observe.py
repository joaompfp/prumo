"""Local-only worker observation receipt. Collects evidence; never closes the incident."""
import argparse
import importlib.util
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/joao/prumo-operations/worker-safety-release-20261123")
DATA = Path("/home/joao/docker/stacks/web/appdata/prumo/prumo.sqlite3")


def validate_gate(expected, actual, now, minimum_seconds):
    """Use identity AND uninterrupted age, not a fresh container's zero restart count."""
    started = datetime.fromisoformat(expected["started"].replace("Z", "+00:00"))
    age = (now - started).total_seconds()
    if actual["Id"] != expected["container"] or actual["Image"] != expected["actual_image"]:
        raise ValueError("worker was replaced during the observation window")
    if not actual["State"]["Running"] or actual["State"]["OOMKilled"] or actual["RestartCount"] != 0:
        raise ValueError("worker stopped, restarted or was OOM-killed during the observation")
    if actual["State"]["StartedAt"] != expected["started"]:
        raise ValueError("worker start changed during the observation window")
    if age < minimum_seconds:
        raise ValueError(f"observation too early: {age:.3f}s elapsed; {minimum_seconds}s required")
    return age


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimum-seconds", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.minimum_seconds < 900:
        raise ValueError("at least one actual scheduler interval is required")
    if args.output.exists():
        raise FileExistsError(args.output)
    expected = json.loads((ROOT / "activated-images.json").read_text())["prumo-ingest"]
    actual = json.loads(subprocess.check_output(["docker", "inspect", "prumo-ingest"]))[0]
    result = {"at": datetime.now(timezone.utc).isoformat(), "minimum_seconds": args.minimum_seconds,
              "historical_cause_closed": False, "incident_accepted": False}
    try:
        result["uninterrupted_seconds"] = validate_gate(expected, actual, datetime.now(timezone.utc), args.minimum_seconds)
        spec = importlib.util.spec_from_file_location("worker_receipts", ROOT / "collect.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load the approved receipt collector")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result["snapshot"] = module.collect()
        conn = sqlite3.connect(DATA.resolve().as_uri() + "?mode=ro&readonly_shm=1", uri=True)
        try:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            result["new_dataset_runs"] = [list(row) for row in conn.execute(
                "SELECT id,source_id,dataset_key,state,started_at,finished_at FROM dataset_run WHERE started_at>=? ORDER BY id",
                (expected["started"][:26] + "+00:00",))]
            result["new_derived_runs"] = [list(row) for row in conn.execute(
                "SELECT * FROM derived_run WHERE started_at>=? ORDER BY id",
                (expected["started"][:26] + "+00:00",))]
            conn.execute("COMMIT")
        finally:
            conn.close()
        result["source_runs_requiring_review"] = [row for row in result["new_dataset_runs"] if row[3] != "verified"]
        result["worker_logs"] = subprocess.check_output(
            ["docker", "logs", "--since", expected["started"], "prumo-ingest"],
            stderr=subprocess.STDOUT, text=True, timeout=60)
        result["observation_evidence_collected"] = True
        result["requires_human_or_controller_review"] = True
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: result.get(k) for k in ("at", "uninterrupted_seconds", "minimum_seconds", "observation_evidence_collected", "error")}))


if __name__ == "__main__":
    main()
