"""Live end-to-end check against Eurostat (network). Deselected by default (pytest.ini adds
-m "not live"); run with:  pytest tests/ingest/test_live_eurostat.py -m live -s"""
import pytest

from ingest import verifiers
from ingest.db import open_db
from ingest.http import RequestsHttp
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources.eurostat import EurostatSource
from ingest.verifiers import register_verifier
from ingest.verifiers.eurostat import EurostatVerifier
from ingest.verify import run_with_refetch
from tests.ingest.eurostat_fixtures import ROOT

LIVE_SERIES = ["eurostat.manufacturing.PT",           # PT monthly industrial production index
               "eurostat.gov_debt_pct_gdp.EU27_2020",  # EU annual government debt
               "eurostat.gdp_quarterly.EU27"]          # EU quarterly GDP (chain-linked volumes)


@pytest.mark.live
def test_live_run_with_refetch(tmp_path, monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})
    reg = {s.id: s for s in load_registry(ROOT / "registry" / "core.yaml")}
    specs = [reg[i] for i in LIVE_SERIES]
    db = open_db(tmp_path / "live.db")
    try:
        sync_registry(db, specs)
        verifier = EurostatVerifier()
        register_verifier(verifier)
        result = run_with_refetch(db, RawStore(tmp_path / "raw"), EurostatSource(), verifier,
                                  specs, RequestsHttp(throttle_rps=1.0), size=50)
        rows = db.conn.execute(
            "SELECT v.dataset_run_id, v.sample_size, v.passed, "
            "SUM(i.match = 0) FROM verification v JOIN verification_item i "
            "ON i.verification_id = v.id GROUP BY v.id ORDER BY v.id").fetchall()
        per_series = db.conn.execute(
            "SELECT series_id, COUNT(*), MIN(period), MAX(period) FROM observation "
            "WHERE dataset_run_id = ? GROUP BY series_id", (result.run_id,)).fetchall()
        bad = db.conn.execute("SELECT series_id, period, expected_text, observed_text, note "
                              "FROM verification_item WHERE match = 0").fetchall()
        print(f"\nfinal state: {result.state}  run_id={result.run_id}  "
              f"written={result.n_written}  quarantined={result.n_quarantined}")
        for run_id, size, passed, n_bad in rows:
            print(f"verification of run {run_id}: sample {size}, passed={bool(passed)}, "
                  f"mismatches={n_bad}")
        for sid, n, lo, hi in per_series:
            print(f"  {sid}: {n} observations {lo}..{hi}")
        for b in bad:
            print("  MISMATCH", b)
        assert result.state == "verified", bad
    finally:
        db.close()
