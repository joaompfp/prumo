"""Live end-to-end check against FRED — network. Deselected by default (pytest.ini adds
-m "not live"); run with the owner's key in the environment ONLY:

    FRED_API_KEY=... .venv-ci/bin/python -m pytest tests/ingest/test_live_fred.py -m live -s

Runs the real pipeline over ALL 12 active core series: the registered FredVerifier re-reads a
fresh random sample through the independent keyless table channel
(https://fred.stlouisfed.org/data/<CODE>). Bounded: RequestsHttp throttles <=1 req/s, each
call times out at 120 s, ONE whole-dataset attempt (max_attempts=1), sample size 120. The
licence gate keeps served=0 even when verified (IMF grant unconfirmed). The controller
re-runs this from the planned f0nix egress after review; a skip means no owner key was in the
environment.
"""
import base64
import json
import os

import pytest

from ingest.db import open_db
from ingest.http import RequestsHttp
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources.fred import FredSource
from ingest.verifiers import register_verifier
from ingest.verifiers.fred import FredVerifier, read_table_page
from ingest.verify import run_with_refetch
from tests.ingest.fred_fixtures import ROOT, active_specs


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
        http = RequestsHttp(throttle_rps=1.0, timeout=120.0)
        result = run_with_refetch(db, RawStore(tmp_path / "raw"), FredSource(api_key=key),
                                  verifier, specs, http, size=120, max_attempts=1)
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
        assert all(n == 417 and (lo, hi) == ("1992-01", "2026-09")
                   for _, n, lo, hi in per_series)
        assert served == 0  # redistribution_ok=false: verified is not served
        assert verifs == [(120, 1)]
        assert quar == [("non_numeric", 12 * 144)]  # the API's '.' pre-1992 missing cells
        # offline evidence replay (no HTTP): every sampled item's archived envelope re-reads
        rows = db.conn.execute(
            "SELECT evidence_url, evidence_sha256 FROM verification_item").fetchall()
        id_of = {s.native_code: s.id for s in specs}
        store = RawStore(tmp_path / "raw")
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
        assert replayed == 120
    finally:
        db.close()
