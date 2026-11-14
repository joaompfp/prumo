"""Live end-to-end check against BPstat (Banco de Portugal) — network. Deselected by default
(pytest.ini adds -m "not live"); run with:

    .venv-ci/bin/python -m pytest tests/ingest/test_live_bportugal.py -m live -s

Runs the real pipeline end to end over ALL 10 active core series: the registered
BPortugalVerifier re-reads a fresh random sample of each run through the independent portal
channel (/api/observations/ + /api/series/); run_with_refetch must end `verified` and every
series must be served. Public endpoints are unauthenticated and fast; RequestsHttp throttles to
<=1 req/s and times each call out at 50 s (the registry declares no timeout_s).
"""
import pytest

from ingest.db import open_db
from ingest.http import RequestsHttp
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources.bportugal import BPortugalSource
from ingest.verifiers import register_verifier
from ingest.verifiers.bportugal import BPortugalVerifier
from ingest.verify import run_with_refetch
from tests.ingest.bportugal_fixtures import ROOT

LIVE_SERIES = ["bportugal.euribor_1m.EA", "bportugal.euribor_3m.EA", "bportugal.euribor_6m.EA",
               "bportugal.euribor_12m.EA", "bportugal.eur_usd.EA", "bportugal.pt_10y.PT",
               "bportugal.de_10y.DE", "bportugal.credit_housing.PT",
               "bportugal.credit_consumer.PT", "bportugal.deposits_households.PT"]


@pytest.mark.live
def test_live_run_with_refetch_is_verified_and_served(tmp_path, monkeypatch):
    from ingest import verifiers
    monkeypatch.setattr(verifiers, "_REGISTRY", {})
    verifier = BPortugalVerifier()
    register_verifier(verifier)

    reg = {s.id: s for s in load_registry(ROOT / "registry" / "core.yaml")}
    specs = [reg[i] for i in LIVE_SERIES]
    db = open_db(tmp_path / "live.db")
    try:
        sync_registry(db, specs)
        http = RequestsHttp(throttle_rps=1.0, timeout=50.0)
        result = run_with_refetch(db, RawStore(tmp_path / "raw"), BPortugalSource(), verifier,
                                  specs, http)
        per_series = db.conn.execute(
            "SELECT series_id, COUNT(*), MIN(period), MAX(period) FROM observation "
            "WHERE dataset_run_id = ? GROUP BY series_id", (result.run_id,)).fetchall()
        served = db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0]
        verifs = db.conn.execute(
            "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
            (result.run_id,)).fetchall()
        quar = db.conn.execute(
            "SELECT series_id, reason, COUNT(*) FROM quarantine WHERE dataset_run_id=? "
            "GROUP BY series_id, reason", (result.run_id,)).fetchall()
        print(f"\nfinal state: {result.state}  run_id={result.run_id}  written={result.n_written}"
              f"  quarantined={result.n_quarantined}  served={served}  verifications={verifs}")
        for sid, n, lo, hi in sorted(per_series):
            print(f"  {sid}: {n} observations {lo}..{hi}")
        for sid, reason, n in quar:
            print(f"  quarantine {sid}: {reason} x{n}")
        assert result.state == "verified"
        assert {r[0] for r in per_series} == set(LIVE_SERIES)
        assert all(n > 300 for _, n, _, _ in per_series)
        assert served == result.n_written >= 10 * 300
        assert verifs and all(p == 1 for _, p in verifs)
    finally:
        db.close()
