"""Live end-to-end check against FRED — network. Deselected by default (pytest.ini adds
-m "not live"); run with the owner's key in the environment ONLY:

    FRED_API_KEY=... .venv-ci/bin/python -m pytest tests/ingest/test_live_fred.py -m live -s

Runs the real pipeline over ALL 12 active core series: the registered FredVerifier re-reads a
fresh random sample through the independent keyless table channel
(https://fred.stlouisfed.org/data/<CODE>). Bounded: RequestsHttp throttles <=1 req/s with
client retries DISABLED (retries=0) and a 120 s PER-REQUEST timeout - that bounds each call,
it is not a whole-phase deadline (none is implemented here; the controller's f0nix acceptance
caps the phase at 48 calls / 180 s) - plus ONE whole-dataset attempt (max_attempts=1) and
sample size 120. The licence gate keeps served=0 even when verified (IMF grant unconfirmed).

Non-stale by construction: FRED publishes a new month every cycle, so NO per-series row
counts, date ranges or '.' quarantine totals are frozen here - they are re-derived from the
run's OWN archived publisher responses (raw-store bytes re-parsed offline) and must match the
DB exactly (nonempty series, canonical periods, exact latest/sampled values via the verifier).
The controller re-runs this from the planned f0nix egress after review; a skip means no owner
key was in the environment.
"""
import base64
import json
import os
import re
from pathlib import Path

import pytest

from ingest.db import open_db
from ingest.http import RequestsHttp
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources import RawResponse
from ingest.sources.fred import FredSource
from ingest.verifiers import register_verifier
from ingest.verifiers.fred import FredVerifier, read_table_page
from ingest.verify import run_with_refetch
from tests.ingest.fred_fixtures import ROOT, active_specs

_PERIOD = re.compile(r"[0-9]{4}-[0-9]{2}")  # canonical YYYY-MM (source asserts ASCII dates)


@pytest.mark.live
def test_live_run_with_refetch_is_verified_and_served_zero(tmp_path, monkeypatch):
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        pytest.skip("owner FRED_API_KEY not in the environment (never read from any file)")
    from ingest import verifiers
    monkeypatch.setattr(verifiers, "_REGISTRY", {})  # self-empty registry, pytest fixture only
    verifier = FredVerifier()
    register_verifier(verifier)

    reg = {s.id: s for s in load_registry(ROOT / "registry" / "core.yaml")}
    fixtures = active_specs()  # the test helper reads the same registry; ids, not mappings
    specs = [reg[s.id] for s in fixtures]
    assert len(specs) == 12 and all(s.active for s in specs)
    db = open_db(tmp_path / "live.db")
    try:
        sync_registry(db, specs)
        http = RequestsHttp(throttle_rps=1.0, timeout=120.0, retries=0)  # per-request bound
        result = run_with_refetch(db, RawStore(tmp_path / "raw"), FredSource(api_key=key),
                                  verifier, specs, http, size=120, max_attempts=1)
        store = RawStore(tmp_path / "raw")
        per_series = db.conn.execute(
            "SELECT series_id, COUNT(*), MIN(period), MAX(period) FROM observation "
            "WHERE dataset_run_id = ? GROUP BY series_id", (result.run_id,)).fetchall()
        served = db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0]
        verifs = db.conn.execute(
            "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
            (result.run_id,)).fetchall()
        quar = db.conn.execute(
            "SELECT reason, COUNT(*) FROM quarantine WHERE dataset_run_id=? GROUP BY reason",
            (result.run_id,)).fetchall()
        print(f"\nfinal state: {result.state}  run_id={result.run_id}  "
              f"written={result.n_written}  quarantined={result.n_quarantined}  "
              f"served={served}  verifications={verifs}")
        for sid, n, lo, hi in sorted(per_series):
            print(f"  {sid}: {n} observations {lo}..{hi}")
        for reason, n in quar:
            print(f"  quarantine: {reason} x{n}")
        assert result.state == "verified"
        assert {r[0] for r in per_series} == {s.id for s in specs}
        # Non-stale expectations derived from the run's OWN archived publisher bytes (never
        # frozen 417/2026-09 counts: FRED publishes a new month every cycle). Re-parsing the
        # raw store offline asserts DB == publisher archive exactly, incl. row loss anywhere
        # between fetch and write; value correctness past identity is the verifier's job.
        raws = db.conn.execute(
            "SELECT url, params_json, path FROM raw_fetch WHERE dataset_run_id=? AND ok=1 "
            "ORDER BY id", (result.run_id,)).fetchall()
        responses = [RawResponse(url=url, params=json.loads(params_json), status=200,
                                 body=store.load(Path(path))) for url, params_json, path in raws]
        expected = FredSource(api_key=key).parse(specs, responses)  # offline, no HTTP
        metas = {}
        for url, params_json, path in raws:  # /fred/series responses carry no limit param
            p = json.loads(params_json)
            if set(p) == {"series_id", "file_type"}:
                metas[p["series_id"]] = json.loads(store.load(Path(path)))
        sid_to_code = {s.id: s.native_code for s in specs}
        for sid, n, lo, hi in per_series:
            arch = expected[sid]
            vals = [r for r in arch if r.value_raw is not None]
            assert vals, f"{sid}: archived publisher response holds no values"
            assert n == len(vals), f"{sid}: DB holds {n} rows != {len(vals)} archived values"
            assert (lo, hi) == (vals[0].period_raw, vals[-1].period_raw)
            assert _PERIOD.fullmatch(lo) and _PERIOD.fullmatch(hi)
            meta = metas[sid_to_code[sid]]["seriess"][0]
            assert (meta["observation_start"][:7], meta["observation_end"][:7]) == (lo, hi), \
                f"{sid}: DB range {lo}..{hi} != the publisher-declared metadata extent"
        assert served == 0  # redistribution_ok=false: verified is not served
        assert verifs == [(120, 1)]
        # the API's '.' missing cells are quarantined non_numeric, exactly as many as archived
        assert quar == [("non_numeric", sum(r.value_raw is None
                                            for rows in expected.values() for r in rows))]
        # offline evidence replay (no HTTP): every sampled item's archived envelope re-reads
        rows = db.conn.execute(
            "SELECT evidence_url, evidence_sha256 FROM verification_item").fetchall()
        id_of = {s.native_code: s.id for s in specs}
        replayed = 0
        for url, sha in rows:
            blob = store.load(store.root / "verify-fred" / sha[:2] / sha)
            rec = json.loads(blob)["table"]
            assert rec["url"] == url and rec["status"] == 200
            code = url.rsplit("/", 1)[-1]
            unit, values = read_table_page(base64.b64decode(rec["body_b64"], validate=True),
                                           code, reg[id_of[code]])
            assert unit and values
            replayed += 1
        print(f"  offline evidence replay: {replayed} envelopes re-read without HTTP")
        assert replayed == len(rows) == 120  # every sampled item's envelope, value + unit
    finally:
        db.close()
