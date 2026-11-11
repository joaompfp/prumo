"""Live end-to-end check against INE (network). Deselected by default (pytest.ini adds
-m "not live"); run with:  pytest tests/ingest/test_live_ine.py -m live -s

Runs the real pipeline end to end: the registered INEVerifier re-reads a fresh random sample of
each run through the independent bddXplorer table channel; run_with_refetch must end `verified`
and the series must be served.
"""
import pytest

from ingest.db import open_db
from ingest.http import RequestsHttp
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources.ine import INESource
from ingest.verifiers import register_verifier
from ingest.verifiers.ine import INEVerifier
from ingest.verify import run_with_refetch
from tests.ingest.ine_fixtures import ROOT

LIVE_SERIES = ["ine.unemployment_monthly.PT",   # monthly, latest month provisional ('&')
               "ine.conf_manufacturing.PT",     # monthly confidence indicator
               "ine.ipi_seasonal_cae_C.PT",     # monthly IPI, manufacturing
               "ine.ipi_seasonal_cae_10.PT",    # IPI CAE *division* (verifier's deep injection)
               "ine.live_births.PT"]            # annual


@pytest.mark.live
def test_live_run_with_refetch_is_verified_and_served(tmp_path, monkeypatch):
    from ingest import verifiers
    monkeypatch.setattr(verifiers, "_REGISTRY", {})
    register_verifier(INEVerifier())

    reg = {s.id: s for s in load_registry(ROOT / "registry" / "core.yaml")}
    specs = [reg[i] for i in LIVE_SERIES]
    db = open_db(tmp_path / "live.db")
    try:
        sync_registry(db, specs)
        # INE's JSON API answers in 15-45 s per request (registry ine.timeout_s: 300);
        # the bddXplorer table is fast, and RequestsHttp throttles to <=1 req/s
        result = run_with_refetch(db, RawStore(tmp_path / "raw"), INESource(), INEVerifier(),
                                  specs, RequestsHttp(throttle_rps=1.0), size=24)
        per_series = db.conn.execute(
            "SELECT series_id, COUNT(*), MIN(period), MAX(period), "
            "SUM(status_flag = 'provisional') FROM observation WHERE dataset_run_id = ? "
            "GROUP BY series_id", (result.run_id,)).fetchall()
        served = db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0]
        [(n_items, passed)] = db.conn.execute(
            "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
            (result.run_id,)).fetchall()
        print(f"\nfinal state: {result.state}  run_id={result.run_id}  written={result.n_written} "
              f" quarantined={result.n_quarantined}  served={served}  verification: "
              f"{n_items} items, passed={passed}")
        for sid, n, lo, hi, prov in per_series:
            print(f"  {sid}: {n} observations {lo}..{hi} (provisional: {prov})")
        assert result.state == "verified"
        assert {r[0] for r in per_series} == set(LIVE_SERIES)
        assert served >= len(LIVE_SERIES)
        assert passed == 1
    finally:
        db.close()
