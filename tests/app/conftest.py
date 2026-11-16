"""A small served database and a TestClient for the public site.

The database is built through the real `Db` write paths (registry sync, verified runs, a derived
run) on a file in `tmp_path`, then closed; the app opens it strictly read-only, exactly like
production. Values are the publisher's tokens, so the tests check the bytes that reach the page.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from ingest.db import open_db
from ingest.models import Observation, SeriesSpec, SourceSpec
from ingest.registry import sync_derived, sync_registry
from tests.ingest.derived_helpers import derived_spec

T1 = "2026-11-01T09:00:00+00:00"
T2 = "2026-11-02T09:00:00+00:00"
T3 = "2026-11-03T09:00:00+00:00"
T4 = "2026-11-04T09:00:00+00:00"

INE = SourceSpec(name="ine", licence="CC BY 4.0", licence_url="https://www.ine.pt/x/terms",
                 attribution="INE - Instituto Nacional de Estatística", redistribution_ok=True)
EUROSTAT = SourceSpec(name="eurostat", licence="CC BY 4.0",
                      licence_url="https://ec.europa.eu/eurostat/terms",
                      attribution="Eurostat", redistribution_ok=True)
REN = SourceSpec(name="ren", licence="Uso restrito", licence_url="https://www.ren.pt/terms",
                 attribution="REN - Redes Energéticas Nacionais", redistribution_ok=False)
WORLDBANK = SourceSpec(name="worldbank", licence="CC BY 4.0",
                       licence_url="https://datacatalog.worldbank.org/public-licenses",
                       attribution="World Bank", redistribution_ok=True)

HICP = "ine.hicp_yoy.PT"
UNEMP = "ine.unemployment_monthly.PT"
XCHECK = "eurostat.hicp_yoy.PT"
INACTIVE = "ine.hicp_yoy.PT.old"
WITHHELD = "ren.electricity_price.PT"
WORLD = "worldbank.gdp_growth.US"
DERIVED = "derived.unemployment_monthly.PT.yoy_change"
SHA = "b" * 64


def make_spec(sid, *, source=INE, key="hicp_yoy.PT.M", role="primary", active=True,
              theme="economy", geography="PT", frequency="M", unit="%"):
    return SeriesSpec(id=sid, source=source, indicator_key=key, role=role, theme=theme,
                      geography=geography, frequency=frequency, unit=unit, active=active)


def fetch(db, sid, values, fetched_at, *, source=INE.name, flag=None, sha=SHA):
    """One verified fetched vintage of `sid` (period -> token), like a real scheduler run."""
    run = db.begin_run(source, f"k-{sid}-{fetched_at}", fetched_at)
    fid = db.record_raw_fetch(source_name=source, run_id=run, url="https://ine.pt/data/x",
                              params_json=None, fetched_at=fetched_at, http_status=200,
                              sha256=sha, path="raw/x", n_bytes=1234, ok=True)
    rows = []
    for period, value in values.items():
        obs = Observation.from_raw(sid, period, value)
        if flag is not None:
            obs = obs.model_copy(update={"status_flag": flag})
        rows.append((obs, fid, fetched_at))
    db.write_observations(run, rows)
    db.set_run_state(run, "verified")
    return run


def _derived_run(db):
    inputs = db.served_fetched_inputs(UNEMP)
    ids = [inputs["2026-09"][0]]
    dsid = next(r["id"] for r in db.derived_series_rows(active_only=False) if r["key"] == DERIVED)
    run = db.begin_derived_run(T4, "cli", [DERIVED])
    db.write_derived_observations(run, T4, [(dsid, "2026-10", "0.3", 1, json.dumps(ids))])
    oid = db.derived_observations_of_run(run)[-1]["id"]
    db.set_derived_row_states([(oid, "match")])
    db.finish_derived_run(run, "verified", T4, n_written=1, n_checked=1, n_mismatch=0)
    return run


def build(path):
    db = open_db(path)
    sync_registry(db, [
        make_spec(HICP),
        make_spec(UNEMP, key="unemployment_rate.PT.M"),
        make_spec(XCHECK, source=EUROSTAT, role="cross_check"),
        make_spec(INACTIVE, active=False),
        make_spec(WITHHELD, source=REN, key="ren_electricity_biomass.PT.M", unit="GWh"),
        make_spec(WORLD, source=WORLDBANK, key="worldbank_gdp_growth.US.A",
                  geography="US", frequency="A"),
    ])
    sync_derived(db, [derived_spec(DERIVED, UNEMP, "yoy_change")])
    fetch(db, HICP, {"2026-08": "2.1", "2026-09": "2.0", "2026-10": "1.9"}, T1)
    run = fetch(db, HICP, {"2026-10": "1.8"}, T3)     # a real revision: 1.9 -> 1.8
    vid = db.add_verification(run, 4242, 3, True, T3, sample_procedure="prumo-sample-v2",
                              sample_design={"n_items": 3}, input_origin="live",
                              verifier_channel="live")
    db.add_verification_item(vid, {
        **{c: None for c in (
            "expected_text", "expected_decimal", "expected_unit", "expected_flag",
            "observed_series_id", "observed_period", "observed_text", "observed_decimal",
            "observed_unit", "observed_flag", "evidence_url", "evidence_sha256", "note",
            "reason", "compared", "unit_not_compared", "flag_not_compared")},
        "series_id": HICP, "period": "2026-10", "match": True})
    fetch(db, UNEMP, {"2026-09": "6.4", "2026-10": "6.2"}, T3, flag="provisional")
    fetch(db, XCHECK, {"2026-10": "1.8"}, T3, source=EUROSTAT.name, sha="c" * 64)
    fetch(db, WITHHELD, {"2026-10": "99.9"}, T3, source=REN.name, sha="d" * 64)
    fetch(db, WORLD, {"2024": "2.3"}, T2, source=WORLDBANK.name, sha="e" * 64)
    _derived_run(db)
    db.close()


@pytest.fixture
def site_path(tmp_path):
    path = tmp_path / "prumo.db"
    build(path)
    return path


@pytest.fixture
def client(site_path):
    with TestClient(create_app(str(site_path))) as test_client:
        yield test_client
