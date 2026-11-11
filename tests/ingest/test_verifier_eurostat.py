"""Eurostat independent verifier (SDMX 2.1 TSV) on recorded real payloads, alone and through
the full pipeline (run_dataset -> verify_run) against the JSON-stat adapter."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from ingest import verifiers
from ingest.db import open_db
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.eurostat import EurostatSource
from ingest.verifiers import BlindItem, get_verifier, register_verifier
from ingest.verifiers.eurostat import EurostatVerifier
from ingest.verifiers.independence import assert_verifier_independent
from ingest.verify import run_with_refetch, verify_run
from tests.ingest.eurostat_fixtures import MANIFEST, FixtureHttp, body, registry_specs, specs_of
from tests.ingest.eurostat_verifier_entry import CASES
from tests.ingest.fakes import FakeHttp, ok

# the four base sets (one per frequency); the confidential_* sets are tested on their own
ALL = ["monthly_sts_inpr_m", "annual_nama_10_pc", "quarterly_namq_10_gdp", "semester_nrg_pc_204"]


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


# --- the channel -------------------------------------------------------------------------------

def test_verifier_reads_tsv_values_and_flags():
    reg = registry_specs()
    items = [BlindItem(sid, period, reg[sid]) for sid, period, _, _ in CASES]
    http = FixtureHttp()
    results = EurostatVerifier().check(items, http)
    assert [(r.series_id, r.period, r.observed_text, r.observed_flag) for r in results] == CASES
    for r in results:
        assert r.observed_decimal == "." and r.observed_unit is None
        assert "/sdmx/2.1/data/" in r.evidence_url and r.evidence_url.endswith("format=TSV")
        assert r.evidence in {body(f"{n}.tsv") for n in ALL}
    assert sorted(set(http.calls)) == sorted(MANIFEST[n]["tsv_url"] for n in ALL)
    # '28560 p' in the TSV -> token '28560' + flag 'provisional'
    assert b"28560 p" in body("annual_nama_10_pc.tsv")


def test_verifier_missing_period_or_series_is_not_found():
    reg = registry_specs()
    items = [BlindItem("eurostat.gdp_quarterly.EU27", "1980-Q1", reg["eurostat.gdp_quarterly.EU27"]),
             BlindItem("eurostat.gdp_quarterly.EU27", "2031-Q1", reg["eurostat.gdp_quarterly.EU27"])]
    for r in EurostatVerifier().check(items, FixtureHttp()):
        assert r.observed_text is None and r.observed_flag is None


@pytest.mark.parametrize("raw", [body("sdmx_404_fault.xml"), body("error_404_unknown_dataset.json"),
                                 b"<!DOCTYPE html><html><body>down</body></html>", b"",
                                 b"no header here\n"])
def test_verifier_rejects_non_tsv(raw):
    reg = registry_specs()
    item = BlindItem("eurostat.gdp_quarterly.EU27", "2026-Q3", reg["eurostat.gdp_quarterly.EU27"])
    url = MANIFEST["quarterly_namq_10_gdp"]["tsv_url"]
    with pytest.raises(ValueError):
        EurostatVerifier().check([item], FixtureHttp({url: raw}))


def test_verifier_raises_on_http_error_status():
    reg = registry_specs()
    item = BlindItem("eurostat.gdp_quarterly.EU27", "2026-Q3", reg["eurostat.gdp_quarterly.EU27"])
    with pytest.raises(ValueError, match="HTTP 404"):
        EurostatVerifier().check([item], FakeHttp(ok(body("sdmx_404_fault.xml"), status=404)))


def test_verifier_rejects_unknown_flag_on_a_value():
    url = MANIFEST["annual_nama_10_pc"]["tsv_url"]
    raw = body("annual_nama_10_pc.tsv").replace(b"28560 p", b"28560 x")
    reg = registry_specs()
    item = BlindItem("eurostat.gdp_per_capita_eur.PT", "2025", reg["eurostat.gdp_per_capita_eur.PT"])
    with pytest.raises(ValueError, match="unknown Eurostat flag"):
        EurostatVerifier().check([item], FixtureHttp({url: raw}))


@pytest.mark.parametrize("name, sid, conf_period, ok_period", [
    ("confidential_c_sts_inpr_m", "eurostat.STS_INPR_M_C.IE", "2014-12", "2024-01"),
    ("confidential_n_sts_inpr_m", "eurostat.metals.PT", "2026-09", "2026-07"),
])
def test_confidential_tsv_cell_is_not_found(name, sid, conf_period, ok_period):
    assert b": @" in body(f"{name}.tsv")
    reg = registry_specs()
    a, b = EurostatVerifier().check([BlindItem(sid, conf_period, reg[sid]),
                                     BlindItem(sid, ok_period, reg[sid])], FixtureHttp())
    assert (a.observed_text, a.observed_flag) == (None, None)  # would be a mismatch if sampled
    assert b.observed_text is not None and b.observed_flag == "normal"


@pytest.mark.parametrize("cell", [": @X", "1.0 @Q"])
def test_unknown_tsv_confidentiality_code_raises(cell):
    url = MANIFEST["annual_nama_10_pc"]["tsv_url"]
    raw = body("annual_nama_10_pc.tsv").replace(b"28560 p", cell.encode())
    reg = registry_specs()
    item = BlindItem("eurostat.gdp_per_capita_eur.PT", "2025", reg["eurostat.gdp_per_capita_eur.PT"])
    with pytest.raises(ValueError, match="confidentiality"):
        EurostatVerifier().check([item], FixtureHttp({url: raw}))


def test_conflicting_duplicate_tsv_rows_raise():
    url = MANIFEST["annual_nama_10_pc"]["tsv_url"]
    raw = body("annual_nama_10_pc.tsv")
    pt_row = next(ln for ln in raw.split(b"\n") if ln.startswith(b"A,CP_EUR_HAB,B1GQ,PT"))
    raw = raw.rstrip(b"\n") + b"\n" + pt_row.replace(b"28560 p", b"99999 p") + b"\n"
    reg = registry_specs()
    item = BlindItem("eurostat.gdp_per_capita_eur.PT", "2025", reg["eurostat.gdp_per_capita_eur.PT"])
    with pytest.raises(ValueError, match="conflicting rows"):
        EurostatVerifier().check([item], FixtureHttp({url: raw}))


def test_confidential_cells_are_never_sampled(db, tmp_path):
    """Confidential cells are quarantined (no observation), and the sample is drawn from written
    observations only, so the verifier's 'not found' for ': @C' can never fail a clean run."""
    specs = specs_of("confidential_c_sts_inpr_m", "confidential_n_sts_inpr_m")
    sync_registry(db, specs)
    store, clock = RawStore(tmp_path / "raw"), Clock()
    r = run_dataset(db, store, EurostatSource(), specs, FixtureHttp(), clock)
    assert r.state == "pending-verification" and r.n_quarantined == 62
    assert verify_run(db, r.run_id, EurostatVerifier(), FixtureHttp(), seed=5, size=10_000,
                      specs=specs, store=store, now=clock)
    [(n,)] = q(db, "SELECT sample_size FROM verification WHERE dataset_run_id=?", r.run_id)
    assert n == r.n_written


# --- registration and independence ---------------------------------------------------------------

def test_verifier_registers_and_passes_allowlist():
    v = EurostatVerifier()
    register_verifier(v)  # static allowlist + no shared module with ingest/sources/eurostat.py
    assert get_verifier("eurostat") is v


def test_subprocess_independence():
    assert_verifier_independent("ingest.verifiers.eurostat",
                                "tests.ingest.eurostat_verifier_entry:run",
                                source_name="eurostat",
                                blocked_prefixes=("collectors", "ingest.flags"))


# --- through the pipeline ----------------------------------------------------------------------------

@pytest.fixture
def env(db, tmp_path):
    specs = specs_of(*ALL)
    sync_registry(db, specs)
    return db, specs, RawStore(tmp_path / "raw"), Clock()


def test_verifier_matches_clean_run(env):
    db, specs, store, clock = env
    r = run_dataset(db, store, EurostatSource(), specs, FixtureHttp(), clock)
    assert r.state == "pending-verification" and r.n_written > 1000
    assert verify_run(db, r.run_id, EurostatVerifier(), FixtureHttp(), seed=7, size=200,
                      specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "verified"
    [(n, passed)] = q(db, "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?", r.run_id)
    assert passed == 1 and n == 200
    flags = {f for (f,) in q(db, "SELECT DISTINCT expected_flag FROM verification_item")}
    assert "normal" in flags
    # every item compared a flag, and its evidence (the TSV) is in the raw store
    assert q(db, "SELECT COUNT(*) FROM verification_item WHERE observed_flag IS NULL "
                 "OR evidence_sha256 IS NULL") == [(0,)]


def test_verifier_matches_every_observation_of_a_clean_run(env):
    db, specs, store, clock = env
    r = run_dataset(db, store, EurostatSource(), specs, FixtureHttp(), clock)
    assert verify_run(db, r.run_id, EurostatVerifier(), FixtureHttp(), seed=1, size=10_000,
                      specs=specs, store=store, now=clock)
    [(n,)] = q(db, "SELECT sample_size FROM verification WHERE dataset_run_id=?", r.run_id)
    assert n == r.n_written  # all of them, flags provisional/estimated/break included


def _tampered_run(env, old: bytes, new: bytes):
    db, specs, store, clock = env
    url = MANIFEST["annual_nama_10_pc"]["json_url"]
    raw = body("annual_nama_10_pc.json")
    assert raw.count(old) == 1
    r = run_dataset(db, store, EurostatSource(), specs,
                    FixtureHttp({url: raw.replace(old, new)}), clock)
    assert r.state == "pending-verification"
    return r


def test_verifier_detects_tampered_value(env):
    # PT 2025 is the latest period of its series, so it is always in the sample
    r = _tampered_run(env, b'"152":28560}', b'"152":28570}')
    db, specs, store, clock = env
    assert not verify_run(db, r.run_id, EurostatVerifier(), FixtureHttp(), seed=3, size=20,
                          specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "failed-verification"
    bad = q(db, "SELECT series_id, period, expected_text, observed_text, note FROM "
                "verification_item WHERE match=0")
    assert bad == [("eurostat.gdp_per_capita_eur.PT", "2025", "28570", "28560", "value differs")]
    assert q(db, "SELECT COUNT(*) FROM served_observation WHERE series_id LIKE 'eurostat.%'") \
        == [(0,)]


def test_verifier_detects_tampered_flag(env):
    db, specs, store, clock = env
    # drop the 'p' status of DE 2025 from the JSON-stat payload: stored 'normal', TSV says 'p'
    doc_url = MANIFEST["annual_nama_10_pc"]["json_url"]
    doc = json.loads(body("annual_nama_10_pc.json"), parse_float=str, parse_int=str)
    cat = doc["dimension"]
    n_time = len(cat["time"]["category"]["index"])
    de_2025 = (int(cat["geo"]["category"]["index"]["DE"]) * n_time
               + int(cat["time"]["category"]["index"]["2025"]))
    assert doc["status"].pop(str(de_2025)) == "p"
    raw = json.dumps(doc).encode()  # values become JSON strings; the parser keeps them as tokens
    r = run_dataset(db, store, EurostatSource(), specs, FixtureHttp({doc_url: raw}), clock)
    assert verify_run(db, r.run_id, EurostatVerifier(), FixtureHttp(), seed=3, size=20,
                      specs=specs, store=store, now=clock) is False
    [(sid, period, note)] = q(db, "SELECT series_id, period, note FROM verification_item "
                                  "WHERE match=0")
    assert (sid, period) == ("eurostat.gdp_per_capita_eur.DE", "2025")
    assert note.startswith("flag differs")


def test_run_with_refetch_uses_registered_verifier(env):
    db, specs, store, clock = env
    v = EurostatVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, EurostatSource(), v, specs, FixtureHttp(), size=30, now=clock)
    assert res.state == "verified"
