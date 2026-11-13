"""Controller-only Task17 acceptance. Never writes production or invents publisher responses."""

import base64
import contextlib
import hashlib
import io
import json
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, "/home/joao/projects/prumo-pipeline")
from ingest.cli import main
from ingest.db import open_db
from ingest.http import HttpResult
from ingest.rawstore import RawStore
from ingest.registry import load_registry
from ingest.status import build_status
from ingest.verify import replay_item

ROOT = Path("/home/joao/projects/prumo-pipeline")
OUT = Path(
    tempfile.mkdtemp(
        prefix="prumo-t17-" + sys.argv[1] + "-", dir="/home/joao/.hermes/cache/scratch"
    )
)
REG = load_registry(ROOT / "registry/core.yaml")
REMOTE = """import base64,json,sys,urllib.request
p=json.load(sys.stdin)
r=urllib.request.urlopen(urllib.request.Request(p['url'],headers={'User-Agent':'prumo-ingest/1.0'}),timeout=p['timeout'])
b=r.read(2*1024*1024+1)
if len(b)>2*1024*1024: raise ValueError('response cap')
print(json.dumps({'status':r.status,'url':r.url,'body':base64.b64encode(b).decode()}))"""


class Bridge:
    def __init__(self, cap=350, deadline=540):
        self.start = time.monotonic()
        self.last = 0
        self.records = []
        self.cap = cap
        self.deadline = deadline

    def get(self, url, params=None, headers=None, timeout=None):
        left = self.deadline - (time.monotonic() - self.start)
        if len(self.records) >= self.cap or left <= 1:
            raise RuntimeError("controller egress budget exhausted")
        time.sleep(max(0, 1 - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        full = url + ("?" + urlencode(params) if params else "")
        p = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", "f0nix", "python3", "-c", shlex.quote(REMOTE)],
            input=json.dumps({"url": full, "timeout": min(10, left)}),
            capture_output=True,
            text=True,
            timeout=min(15, left),
        )
        if p.returncode:
            raise RuntimeError("f0nix egress: " + p.stderr[-600:])
        r = json.loads(p.stdout)
        body = base64.b64decode(r["body"])
        self.records.append(
            {
                "url": url,
                "params": params,
                "final_url": r["url"],
                "status": r["status"],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
            }
        )
        return HttpResult(r["status"], body, r["url"])


def call(args, **kw):
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        rc = main(args, **kw)
    return rc, log.getvalue()


def offline_audit(db, store, source):
    items = db.conn.execute(
        "SELECT i.id,i.evidence_sha256 FROM verification_item i JOIN verification v ON v.id=i.verification_id JOIN dataset_run r ON r.id=v.dataset_run_id JOIN source s ON s.id=r.source_id WHERE s.name=?",
        (source,),
    ).fetchall()
    for iid, sha in items:
        assert replay_item(db, store, iid)
    return len(items), len({sha for _, sha in items})


def counts(db):
    return {
        "observations": db.conn.execute("SELECT count(*) FROM observation").fetchone()[0],
        "served": db.conn.execute("SELECT count(*) FROM served_observation").fetchone()[0],
        "quarantine": db.conn.execute("SELECT count(*) FROM quarantine").fetchone()[0],
    }


def integrity(db):
    assert db.conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert db.conn.execute("PRAGMA foreign_key_check").fetchall() == []


def raw_exact(db, source):
    from collections import Counter

    expected = set()
    occurrences = Counter()
    bynative = {s.native_code: s.id for s in REG if s.active and s.source.name == source}
    for rid, sha, path in db.conn.execute("SELECT id,sha256,path FROM raw_fetch"):
        b = Path(path).read_bytes()
        assert hashlib.sha256(b).hexdigest() == sha
        d = json.loads(b, parse_float=str, parse_int=str)
        if source == "eredes" and isinstance(d, dict) and "results" in d:
            for r in d["results"]:
                for f in ("dgm", "pre", "total"):
                    sid = bynative["energia-produzida-total-nacional:" + f]
                    expected.add((sid, r["datahora"], r[f], rid))
                    occurrences[(sid, r["datahora"], rid)] += 1
        if source == "worldbank" and isinstance(d, list) and len(d) == 2 and isinstance(d[1], list):
            for r in d[1]:
                sid = bynative.get(r["indicator"]["id"] + ":" + r["countryiso3code"])
                if sid and r["value"] is not None:
                    expected.add((sid, r["date"], r["value"], rid))
    actual = set(
        db.conn.execute(
            "SELECT o.series_id,o.period,o.value_text,o.raw_fetch_id FROM observation o JOIN series s ON s.id=o.series_id JOIN source p ON p.id=s.source_id WHERE p.name=? AND o.kind='fetched'",
            (source,),
        )
    )
    assert actual <= expected, (len(actual), len(expected))
    if source == "eredes":
        ambiguous = {x for x in expected if occurrences[(x[0], x[1], x[3])] > 1}
        eligible = expected - ambiguous
        assert actual == eligible, (len(actual), len(eligible))
        q = db.conn.execute(
            "SELECT series_id,raw_period,raw_value FROM quarantine WHERE reason='duplicate_period'"
        ).fetchall()
        assert set(q) == {(sid, ts, value) for sid, ts, value, _ in ambiguous}
        assert len(q) == sum(n for n in occurrences.values() if n > 1)
    return len(actual)


def legacy_hash(db):
    h = hashlib.sha256()
    for row in db.conn.execute(
        "SELECT id,series_id,period,value_text,value,status_flag,kind,dataset_run_id,raw_fetch_id,fetched_at,released_at FROM observation WHERE kind='legacy-unverified' ORDER BY id"
    ):
        h.update(json.dumps(row, separators=(",", ":")).encode())
    return h.hexdigest()


mode = sys.argv[1]
summary = {
    "mode": mode,
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "root": str(OUT),
    "not_deployment": True,
}
if mode == "eredes-live":
    bridge = Bridge()
    dbp = OUT / "prumo.sqlite3"
    raw = OUT / "raw"
    rc, log = call(
        [
            "--db",
            str(dbp),
            "--raw-dir",
            str(raw),
            "run",
            "eredes",
            "--from",
            "2026-04-01",
            "--to",
            "2026-11-11",
        ],
        http_for=lambda _: bridge,
    )
    summary.update(
        exit_code=rc,
        output=log,
        network_requests=len(bridge.records),
        network_seconds=round(time.monotonic() - bridge.start, 3),
        requests=bridge.records,
    )
    db = open_db(dbp)
    store = RawStore(raw)
    summary.update(counts(db))
    summary["exact_original_tuples"] = raw_exact(db, "eredes")
    summary["offline_comparisons"], summary["evidence_bundles"] = offline_audit(db, store, "eredes")
    summary["periods"] = db.conn.execute(
        "SELECT min(period),max(period),count(DISTINCT period) FROM observation"
    ).fetchone()
    summary["sources"] = db.conn.execute(
        "SELECT s.name,count(*) FROM observation o JOIN series x ON x.id=o.series_id JOIN source s ON s.id=x.source_id GROUP BY s.name"
    ).fetchall()
    summary["run_states"] = db.conn.execute(
        "SELECT id,state,input_origin FROM dataset_run"
    ).fetchall()
    integrity(db)
    db.close()
    assert rc == 0, summary
elif mode == "wb-recorded":
    # Repackage ONLY responses with original, precise request timestamps in the old audit capsule.
    wanted = {"NY.GDP.MKTP.KD.ZG", "SL.UEM.TOTL.ZS"}
    with tarfile.open(
        ROOT
        / "docs/superpowers/handoff/reports/evidence/task-13-csv-language/full-recorded-run.tar.gz"
    ) as tf:
        members = tf.getmembers()
        assert len(members) <= 150
        bodies = {}
        for m in members:
            if m.isfile() and m.name.startswith("raw/"):
                assert m.size < 3 * 1024 * 1024
                body = tf.extractfile(m).read()
                bodies[hashlib.sha256(body).hexdigest()] = body
                if m.name.startswith("raw/verify-worldbank/"):
                    env = json.loads(body)
                    for r in env["responses"]:
                        bb = base64.b64decode(r["body_base64"])
                        bodies[hashlib.sha256(bb).hexdigest()] = bb
        reqs = json.loads(tf.extractfile("es-requests.json").read())
    bundle = OUT / "bundle"
    entries = []
    for r in reqs:
        url = r.get("requested_url", r["url"])
        code = url.split("/indicator/")[1].split("?")[0]
        if code not in wanted:
            continue
        fetched = r.get("ts_end") or r.get("start")
        assert isinstance(fetched, str) and datetime.fromisoformat(fetched).tzinfo is not None, r
        body = bodies[r["sha256"]]
        assert len(body) == r["bytes"] and r["status"] == 200
        rel = "responses/" + r["sha256"][:2] + "/" + r["sha256"]
        p = bundle / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
        entries.append(
            {
                "url": url,
                "params": r.get("params"),
                "final_url": r["url"],
                "status": r["status"],
                "fetched_at": fetched,
                "bytes": len(body),
                "sha256": r["sha256"],
                "file": rel,
            }
        )
    assert len(entries) == 4
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "prumo-bundle",
                "version": 1,
                "source": "worldbank",
                "note": "Controller repackage of exact archived original HTTP responses with their original precise request timestamps; not a fresh capture. No timestamp invented for the other 16 archives.",
                "entries": entries,
                "failures": [],
            },
            indent=2,
        )
    )
    dbp = OUT / "prumo.sqlite3"
    raw = OUT / "raw"
    args = ["--db", str(dbp), "--raw-dir", str(raw)]
    rc, log = call(args + ["import-legacy", "/home/joao/projects/_legacy_export/indicators.csv"])
    assert rc == 0, log
    db = open_db(dbp)
    beforehash = legacy_hash(db)
    summary["before"] = counts(db)
    summary["before_served_sources"] = db.conn.execute(
        "SELECT p.name,o.kind,count(*),max(o.fetched_at) FROM served_observation o JOIN series s ON s.id=o.series_id JOIN source p ON p.id=s.source_id GROUP BY p.name,o.kind"
    ).fetchall()
    assert all(r[0] == "worldbank" for r in summary["before_served_sources"])
    db.close()

    def ban(event, args):
        if event in ("socket.connect", "socket.getaddrinfo"):
            raise RuntimeError("network forbidden in recorded acceptance")

    sys.addaudithook(ban)
    logs = [log]
    for code in sorted(wanted):
        rc, log = call(args + ["run", "worldbank", "--bundle", str(bundle), "--indicator", code])
        assert rc == 0, log
        logs.append(log)
    db = open_db(dbp)
    assert legacy_hash(db) == beforehash
    summary["after"] = counts(db)
    summary["legacy_rows_unchanged"] = True
    summary["exact_original_tuples"] = raw_exact(db, "worldbank")
    summary["offline_comparisons"], summary["evidence_bundles"] = offline_audit(
        db, RawStore(raw), "worldbank"
    )
    summary["run_states"] = db.conn.execute(
        "SELECT id,state,input_origin FROM dataset_run WHERE dataset_key NOT LIKE ?", ("legacy:%",)
    ).fetchall()
    expected_times = {
        e["sha256"]: datetime.fromisoformat(e["fetched_at"]).astimezone(timezone.utc).isoformat()
        for e in entries
    }
    for sha, fetched in db.conn.execute("SELECT sha256,fetched_at FROM raw_fetch"):
        assert fetched == expected_times[sha], (sha, fetched, expected_times[sha])
    summary["original_receipt_times_preserved"] = True
    summary["served_sources"] = db.conn.execute(
        "SELECT p.name,o.kind,count(*),min(o.fetched_at),max(o.fetched_at) FROM served_observation o JOIN series s ON s.id=o.series_id JOIN source p ON p.id=s.source_id GROUP BY p.name,o.kind"
    ).fetchall()
    status = build_status(db, REG).to_dict()
    (OUT / "status.json").write_text(json.dumps(status, indent=2))
    integrity(db)
    db.close()
    summary.update(
        exit_code=0,
        output="".join(logs),
        network_forbidden=True,
        original_http_entries=len(entries),
        codes=sorted(wanted),
        bundle=str(bundle),
    )
elif mode == "capture-live":
    bundle = OUT / "bundle"
    unused = OUT / "must-not-exist.sqlite3"
    rc, log = call(
        [
            "--db",
            str(unused),
            "capture",
            "eredes",
            "--output",
            str(bundle),
            "--from",
            "2026-11-10",
            "--to",
            "2026-11-10",
            "--timeout",
            "10",
            "--deadline",
            "40",
            "--max-requests",
            "8",
        ]
    )
    assert rc == 0 and not unused.exists(), log
    manifest = json.loads((bundle / "manifest.json").read_text())
    summary["captured_entries"] = len(manifest["entries"])
    summary["capture_output"] = log
    seeds = []
    for i in (1, 2):
        dbp = OUT / f"replay-{i}.sqlite3"
        raw = OUT / f"raw-{i}"

        def ban(event, args):
            if event in ("socket.connect", "socket.getaddrinfo"):
                raise RuntimeError("network forbidden on recorded replay")

        if i == 1:
            sys.addaudithook(ban)
        rc, log = call(
            [
                "--db",
                str(dbp),
                "--raw-dir",
                str(raw),
                "run",
                "eredes",
                "--bundle",
                str(bundle),
                "--from",
                "2026-11-10",
                "--to",
                "2026-11-10",
            ]
        )
        assert rc == 0, log
        db = open_db(dbp)
        summary[f"replay_{i}"] = {
            **counts(db),
            "exact_tuples": raw_exact(db, "eredes"),
            "offline": offline_audit(db, RawStore(raw), "eredes"),
            "output": log,
        }
        seeds.append(db.conn.execute("SELECT seed FROM verification").fetchone()[0])
        integrity(db)
        db.close()
    assert seeds[0] != seeds[1]
    summary.update(
        exit_code=0, two_fresh_seeds=seeds, bundle=str(bundle), network_forbidden_on_replay=True
    )
elif mode == "wb-live":
    from ingest.operations import run_source
    from ingest.registry import sync_registry

    scope = [
        s
        for s in REG
        if s.active and s.source.name == "worldbank" and s.native_code.startswith("SP.POP.TOTL:")
    ]
    bridge = Bridge(cap=4, deadline=45)
    db = open_db(OUT / "prumo.sqlite3")
    store = RawStore(OUT / "raw")
    sync_registry(db, scope)
    outcomes = run_source(
        db, store, "worldbank", scope, http_for=lambda: bridge, max_attempts=1, size=100
    )
    summary.update(
        outcomes=[o.__dict__ for o in outcomes],
        network_requests=len(bridge.records),
        requests=bridge.records,
        network_seconds=round(time.monotonic() - bridge.start, 3),
    )
    summary.update(counts(db))
    summary["exact_original_tuples"] = raw_exact(db, "worldbank")
    if outcomes[0].state == "verified":
        summary["offline_comparisons"], summary["evidence_bundles"] = offline_audit(
            db, store, "worldbank"
        )
    summary["events"] = db.conn.execute("SELECT kind,detail_json FROM event").fetchall()
    integrity(db)
    db.close()
    summary["exit_code"] = 0 if all(o.state == "verified" for o in outcomes) else 1
else:
    raise SystemExit("unknown mode")
(OUT / "report.json").write_text(json.dumps(summary, indent=2))
print(json.dumps({k: v for k, v in summary.items() if k != "requests"}, indent=2))
print("ARTIFACT_ROOT=" + str(OUT))
