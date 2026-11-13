"""Export only World Bank acceptance evidence from the deployed read-only SQLite store.

No network/source calls, application writes or acceptance transition. The resulting JSON
is an audit capsule, not a replacement database. Run on stdin inside the Prumo image.
"""
import base64
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def rows(db, sql, args=()):
    return [dict(row) for row in db.execute(sql, args)]


with sqlite3.connect("file:/data/prumo.sqlite3?mode=ro", uri=True) as db:
    db.row_factory = sqlite3.Row
    db.execute("BEGIN")
    source_id = db.execute("SELECT id FROM source WHERE name='worldbank'").fetchone()[0]
    runs = rows(db, """SELECT * FROM dataset_run WHERE id IN (
        SELECT MAX(id) FROM dataset_run WHERE source_id=? AND state='verified'
        AND input_origin='live' GROUP BY dataset_key) ORDER BY id""", (source_id,))
    ids = [r["id"] for r in runs]
    assert len(ids) == 18, "review unexpected indicator-group scope before acceptance"
    marks = ",".join("?" for _ in ids)
    specs = rows(db, "SELECT * FROM series WHERE source_id=? ORDER BY id", (source_id,))
    observations = rows(db, f"""SELECT id,series_id,period,value_text,status_flag,
        dataset_run_id,raw_fetch_id,fetched_at,released_at,kind FROM observation
        WHERE dataset_run_id IN ({marks}) ORDER BY series_id,period""", ids)
    raw = rows(db, f"SELECT * FROM raw_fetch WHERE dataset_run_id IN ({marks}) ORDER BY id", ids)
    items = rows(db, f"""SELECT i.*, v.dataset_run_id,v.seed,v.sample_size,v.passed
        FROM verification_item i JOIN verification v ON v.id=i.verification_id
        WHERE v.dataset_run_id IN ({marks}) ORDER BY i.id""", ids)
    failures = rows(db, """SELECT r.id,r.dataset_key,r.state,r.started_at,r.finished_at,
        e.kind,e.detail_json FROM dataset_run r LEFT JOIN event e ON e.dataset_run_id=r.id
        WHERE r.source_id=? AND r.state IN ('failed-fetch','failed-verification')
        ORDER BY r.id,e.id""", (source_id,))
    blobs = {}
    for r in raw:
        body = Path(r["path"]).read_bytes()
        assert hashlib.sha256(body).hexdigest() == r["sha256"]
        assert len(body) == r["bytes"]
        blobs[r["sha256"]] = base64.b64encode(body).decode("ascii")
    for item in items:
        sha = item["evidence_sha256"]
        body = (Path("/data/raw/verify-worldbank") / sha[:2] / sha).read_bytes()
        assert hashlib.sha256(body).hexdigest() == sha
        blobs[sha] = base64.b64encode(body).decode("ascii")
    print(json.dumps({
        "schema": "prumo-worldbank-production-evidence", "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "runs": runs, "series": specs, "observations": observations,
        "raw_receipts": raw, "verification_items": items, "historical_failures": failures,
        "blobs_base64": blobs,
        "task_18_closed": False,
    }, sort_keys=True))
