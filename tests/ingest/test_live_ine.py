"""Live end-to-end check against INE (network). Deselected by default (pytest.ini adds
-m "not live"); run with:  pytest tests/ingest/test_live_ine.py -m live -s

INE has no independent verification channel (registry/unverifiable.md), so the run cannot be
verified: it must end `pending-verification` with nothing served."""
import pytest

from ingest.db import open_db
from ingest.http import RequestsHttp
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources.ine import INESource
from tests.ingest.ine_fixtures import ROOT

LIVE_SERIES = ["ine.unemployment_monthly.PT",   # monthly, latest month provisional ('&')
               "ine.conf_manufacturing.PT",     # monthly confidence indicator
               "ine.ipi_seasonal_cae_C.PT",     # monthly IPI, manufacturing
               "ine.live_births.PT"]            # annual


@pytest.mark.live
def test_live_run_is_pending_verification_and_not_served(tmp_path):
    reg = {s.id: s for s in load_registry(ROOT / "registry" / "core.yaml")}
    specs = [reg[i] for i in LIVE_SERIES]
    db = open_db(tmp_path / "live.db")
    try:
        sync_registry(db, specs)
        # INE answers in 15-45 s per request (trade indicators: minutes)
        result = run_dataset(db, RawStore(tmp_path / "raw"), INESource(), specs,
                             RequestsHttp(throttle_rps=1.0, timeout=300))
        per_series = db.conn.execute(
            "SELECT series_id, COUNT(*), MIN(period), MAX(period), "
            "SUM(status_flag = 'provisional') FROM observation WHERE dataset_run_id = ? "
            "GROUP BY series_id", (result.run_id,)).fetchall()
        served = db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0]
        print(f"\nfinal state: {result.state}  run_id={result.run_id}  "
              f"written={result.n_written}  quarantined={result.n_quarantined}  served={served}")
        for sid, n, lo, hi, prov in per_series:
            print(f"  {sid}: {n} observations {lo}..{hi} (provisional: {prov})")
        assert result.state == "pending-verification"
        assert {r[0] for r in per_series} == set(LIVE_SERIES)
        assert served == 0
    finally:
        db.close()
