"""Verify the exact worker safety release without changing production data."""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SERVICES = ("prumo-ingest", "prumo", "prumo-backoffice")
CMS = ("cms_document", "cms_revision", "cms_event", "editorial_page", "editorial_slot", "editorial_event")
ROOT = Path("/home/joao/docker/stacks/web/images/prumo")
RECEIPT = Path("/home/joao/prumo-operations/worker-safety-release-20261123")


def command(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=120)


def verify(before, current, require_all=False):
    result = {"at": datetime.now(timezone.utc).isoformat(), "checks": [], "changed_tables": []}

    def check(label, condition):
        result["checks"].append({"label": label, "passed": bool(condition)})
        if not condition:
            raise AssertionError(label)

    try:
        check("integrity and FK", current["quick_check"] == "ok" and not current["foreign_keys"])
        check("schema and migrations preserved", all(before[k] == current[k] for k in ("schema", "migrations")))
        check("exact approved checkout", current["checkout"] == command(["git", "-C", str(RECEIPT / "code"), "rev-parse", "HEAD"]).strip())
        check("same table inventory", set(before["tables"]) == set(current["tables"]))
        for table in CMS + ("source", "series", "setting", "derived_series", "verification_spec"):
            check(table + " preserved", before["tables"][table] == current["tables"][table])
        result["changed_tables"] = [name for name in before["tables"] if before["tables"][name] != current["tables"][name]]
        if require_all:
            check("all table contents unchanged during activation", not result["changed_tables"])
        rows = json.loads(command(["docker", "inspect", *SERVICES]))
        expected_hash = hashlib.sha256((ROOT / "ingest/db.py").read_bytes()).hexdigest()
        for row in rows:
            name = row["Name"].removeprefix("/")
            old = before["containers"][name]
            check(name + " replaced", row["Id"] != old["id"] and row["Image"] != old["image"])
            check(name + " running without autonomous restart", row["State"]["Running"] and row["RestartCount"] == 0)
            check(name + " actual image equals rebuilt tag", row["Image"] == command(["docker", "image", "inspect", "--format", "{{.Id}}", name + ":latest"]).strip())
            code_hash = command(["docker", "exec", name, "python", "-c", "import hashlib,ingest.db; from pathlib import Path; print(hashlib.sha256(Path(ingest.db.__file__).read_bytes()).hexdigest())"]).strip()
            check(name + " installed persistence bytes", code_hash == expected_hash)
            logs = command(["docker", "logs", "--since", row["State"]["StartedAt"], name])
            check(name + " no fatal/application error", not re.search(r"Fatal Python error|Bus error|Traceback|\bERROR\b|MissingText|database unusable", logs))
            if name == "prumo-ingest":
                env = dict(x.split("=", 1) for x in row["Config"]["Env"] if "=" in x)
                check("worker fatal diagnostics configured", env.get("PYTHONFAULTHANDLER") == "1")
                check("worker fatal diagnostics active in installed Python", command(["docker", "exec", name, "python", "-c", "import faulthandler; print(faulthandler.is_enabled())"]).strip() == "True")
                check("worker scheduler and writer uid", row["Config"]["Cmd"] == ["python", "-u", "-m", "ingest.scheduler"] and row["Config"]["User"] == "1000:1000")
                records = [json.loads(line) for line in logs.splitlines() if line.startswith("{")]
                check("actual scheduler startup pass", any(r.get("schema") == "prumo-scheduler" and r.get("event") == "blocked" and r.get("source") == "dgeg" for r in records))
                check("worker currently owns shared-memory DMS read lock", any(re.search(r"READ\s+" + str(row["State"]["Pid"]) + r"\s+.*\s128\s128$", line) for line in current["locks"]))
                result["worker_started"] = row["State"]["StartedAt"]
                result["worker_age_seconds"] = (datetime.now(timezone.utc) - datetime.fromisoformat(row["State"]["StartedAt"][:26] + "+00:00")).total_seconds()
            else:
                check(name + " healthy", row["State"].get("Health", {}).get("Status") == "healthy")
        for path, expected in json.loads((RECEIPT / "preserved-infra.json").read_text()).items():
            actual = hashlib.sha256(subprocess.check_output(["git", "-C", "/home/joao/docker", "diff", "--binary", "--", path])).hexdigest()
            check("unrelated infrastructure edit preserved: " + path, actual == expected)
        status = command(["docker", "exec", "prumo-ingest", "python", "-m", "ingest", "--db", "/data/prumo.sqlite3", "--raw-dir", "/data/raw", "status", "--json"])
        parsed = json.loads(status)
        (RECEIPT / ("status-" + current["at"].replace(":", "-") + ".json")).write_text(status)
        check("installed worker read-only status succeeds", bool(parsed))
        result["schema_migrations"] = current["migrations"]
        result["tables"] = current["tables"]
        result["historical_cause_closed"] = False
        result["elapsed_24h_accepted"] = False
        return result
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"passed": sum(c["passed"] for c in result["checks"]), "checks": len(result["checks"]), "changed_tables": result["changed_tables"], "error": result.get("error"), "receipt": str(OUTPUT)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-all-tables-unchanged", action="store_true")
    args = parser.parse_args()
    OUTPUT = args.output
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    verify(json.loads(args.baseline.read_text()), json.loads(args.current.read_text()), args.require_all_tables_unchanged)
