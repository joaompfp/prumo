"""REN DataHub verifier tests — recorded portal CSV-export fixtures
(tests/ingest/fixtures/ren/verify/, 2026-11-11)."""
from datetime import datetime, timedelta, timezone

import pytest

import ingest.verifiers as verifiers
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.ren import RenSource
from ingest.verifiers import BlindItem, get_verifier, register_verifier
from ingest.verifiers.independence import assert_verifier_independent
from ingest.verifiers.ren import RenVerifier
from ingest.verify import replay_item, run_with_refetch, verify_run
from tests.ingest.ren_fixtures import FixtureHttp, all_specs, registry_specs
from tests.ingest.ren_verifier_fixtures import VMANIFEST, VerifyFixtureHttp, decode_evidence, vbody
from tests.ingest.replay_helpers import assert_replays_from_evidence


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def _item(sid: str, period: str) -> BlindItem:
    return BlindItem(sid, period, registry_specs()[sid])


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


def test_verifier_reads_every_recorded_case():
    items, expected = [], []
    for sid, period, token, unit in _CASES:
        items.append(_item(sid, period))
        expected.append((sid, period, token, unit))
    results = RenVerifier().check(items, VerifyFixtureHttp())
    assert [(r.series_id, r.period, r.observed_text, r.observed_unit)
            for r in results] == expected
    assert all(r.observed_decimal == "." and r.observed_flag is None and r.evidence
               and r.evidence_url == VMANIFEST[_sets[sid, period]]["url"]
               for r, (sid, period, _, _) in zip(results, _CASES))


_CASES = [  # (series, period, token, unit) — from the archived CSV bytes
    ("ren.electricity_consumption.PT", "2026-09", "4442", "GWh"),
    ("ren.electricity_price_mibel.PT", "2026-09", "143.9", None),
    ("ren.electricity_consumption.PT", "2020-06", "3604", "GWh"),
]
_sets = {("ren.electricity_consumption.PT", "2026-09"): "balance_2026-09",
         ("ren.electricity_price_mibel.PT", "2026-09"): "market_2026-09",
         ("ren.electricity_consumption.PT", "2020-06"): "balance_2020-06"}


def test_verifier_caches_one_fetch_per_chart_and_month():
    http = VerifyFixtureHttp()
    RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09"),
                         _item("ren.electricity_wind.PT", "2026-09"),
                         _item("ren.electricity_price_mibel.PT", "2026-09")], http)
    assert http.calls == ["balance_2026-09", "market_2026-09"]


def test_verifier_evidence_envelope_carries_exact_bytes_url_and_status():
    """ItemResult.evidence is the versioned 'ren-portal-evidence' v1 envelope: the ONE deciding
    CSV response's exact bytes, FINAL url and ACTUAL http status, recoverable offline (no HTTP);
    ItemResult.evidence_url stays that response's final URL."""
    (r,) = RenVerifier().check([_item("ren.electricity_hydro.PT", "2026-09")],
                               VerifyFixtureHttp())
    m = VMANIFEST["balance_2026-09"]
    assert r.evidence_url == m["url"]
    (rec,) = decode_evidence(r.evidence)  # exactly one deciding response
    assert rec == {"url": m["url"], "status": m["status"], "body": vbody(m["file"])}
    assert m["status"] == 200
    assert r.observed_text == "645" and r.observed_unit == "GWh"


def test_verifier_tampered_value_comes_back_verbatim_for_verify_run():
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]).replace(b"CONSUMO,8275,4442,",
                                                    b"CONSUMO,8275,4443,", 1)
    (r,) = RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                               VerifyFixtureHttp({"balance_2026-09": tampered}))
    assert r.observed_text == "4443"  # detection is verify_run's exact Decimal comparison


def test_verifier_month_mismatch_between_header_and_request_raises():
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]).replace(b"set 26 [GWh]", b"ago 26 [GWh]", 1)
    with pytest.raises(ValueError, match="header disagrees"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": tampered}))


def test_verifier_year_mismatch_raises():
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]).replace(b"set 26 [GWh]", b"set 25 [GWh]", 1)
    with pytest.raises(ValueError, match="header disagrees"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": tampered}))


def test_verifier_previous_year_column_header_drift_raises():
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]).replace(b"set 25 [GWh],", b"set 24 [GWh],", 1)
    with pytest.raises(ValueError, match="reference column"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": tampered}))


def test_verifier_duplicate_mapped_label_raises():
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]).replace(
        b"CONSUMO,8275,4442,40433,4164,39153,6.7,3.3\r\n",
        b"CONSUMO,8275,4442,40433,4164,39153,6.7,3.3\r\nCONSUMO,1,2,3,4,5,6,7\r\n", 1)
    with pytest.raises(ValueError, match="repeats the mapped label"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": tampered}))


def test_verifier_missing_target_row_raises():
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]).replace(
        b"\r\nCONSUMO,8275,4442,40433,4164,39153,6.7,3.3\r\n", b"\r\n", 1)
    with pytest.raises(ValueError, match="0 rows"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": tampered}))


# --- malformed-channel guards: markup, garbage and blank-row probes fail closed --------------

def test_verifier_permanent_html_page_raises():
    """The export service answering an HTML page (error/consent/maintenance) is not a table."""
    tampered = b"<!DOCTYPE html><html><body>Service Unavailable</body></html>"
    with pytest.raises(ValueError, match="markup"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": tampered}))


def test_verifier_non_utf8_csv_raises():
    with pytest.raises(ValueError, match="UTF-8"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": b"\xff\xfe\x00not utf-8"}))


def test_verifier_empty_csv_raises():
    with pytest.raises(ValueError, match="no data rows"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": b""}))


def test_verifier_interior_empty_line_raises():
    """A bare CRLF inside the table (a ZERO-CELL row) is an interior blank: an unreviewed table
    break, fail closed. A row filter that drops zero-cell lines BEFORE the blank-row analysis
    would hide this break — the guard runs on the unfiltered CSV rows."""
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]).replace(
        b"\r\nH\xc3\xaddrica 1,", b"\r\n\r\nH\xc3\xaddrica 1,", 1)
    with pytest.raises(ValueError, match="interior blank"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": tampered}))


def test_verifier_interior_comma_blank_line_raises():
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]).replace(
        b"\r\nCONSUMO,8275,", b"\r\n,,,,,,,\r\nCONSUMO,8275,", 1)
    with pytest.raises(ValueError, match="interior blank"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": tampered}))


def test_verifier_trailing_blank_lines_tolerated():
    """The archived shape ends with blank line(s): a blank SUFFIX is tolerated (read from
    evidence), interior blanks are not."""
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]) + b"\r\n\r\n\r\n"
    (r,) = RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                               VerifyFixtureHttp({"balance_2026-09": tampered}))
    assert r.observed_text == "4442"


def test_verifier_malformed_quote_fails_closed():
    """A stray quote must fail closed (strict CSV parse), never be re-assembled into an altered
    table that otherwise passes the mapped-label checks."""
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]) + b'"unterminated\r\n'
    with pytest.raises(ValueError, match="malformed"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")],
                            VerifyFixtureHttp({"balance_2026-09": tampered}))


def test_verifier_market_header_drift_raises():
    tampered = vbody(VMANIFEST["market_2026-09"]["file"]).replace(b",setembro,,2026,", b",agosto,,2026,", 1)
    with pytest.raises(ValueError, match="header"):
        RenVerifier().check([_item("ren.electricity_price_mibel.PT", "2026-09")],
                            VerifyFixtureHttp({"market_2026-09": tampered}))


def test_verifier_market_geography_row_drift_raises():
    tampered = vbody(VMANIFEST["market_2026-09"]["file"]).replace(b"\r\n,PT,ES,PT,ES\r\n",
                                                   b"\r\n,ES,PT,ES,PT\r\n", 1)
    with pytest.raises(ValueError, match="geography"):
        RenVerifier().check([_item("ren.electricity_price_mibel.PT", "2026-09")],
                            VerifyFixtureHttp({"market_2026-09": tampered}))


def test_verifier_non_2xx_raises():
    class Denied(VerifyFixtureHttp):
        def get(self, url, params=None, headers=None, timeout=None):
            from ingest.http import HttpResult
            return HttpResult(status=404, body=b'{"message":"No data available"}', url=url)

    with pytest.raises(ValueError, match="HTTP 404"):
        RenVerifier().check([_item("ren.electricity_consumption.PT", "2026-09")], Denied())


def test_verifier_registers_and_passes_allowlist():
    v = RenVerifier()
    register_verifier(v)  # the static independence allowlist runs here
    assert get_verifier("ren") is v


def test_verifier_registers_even_in_same_process_as_the_source():
    import ingest.sources.ren  # noqa: F401  (loaded: the static allowlist must still pass)
    register_verifier(RenVerifier())


def test_subprocess_independence():
    assert_verifier_independent("ingest.verifiers.ren",
                                "tests.ingest.ren_verifier_entry:run",
                                source_name="ren",
                                blocked_prefixes=("collectors", "ingest.flags", "ingest.sources"))


# --- through the pipeline -----------------------------------------------------------------------

@pytest.fixture
def env(db, tmp_path):
    specs = all_specs()
    sync_registry(db, specs)
    return db, specs, RawStore(tmp_path / "raw"), Clock()


def _run(env, seed=7):
    db, specs, store, clock = env
    r = run_dataset(db, store, RenSource(periods=("2026-09",)), specs, FixtureHttp(), clock)
    assert r.state == "pending-verification" and r.n_written == 14
    ok = verify_run(db, r.run_id, RenVerifier(), VerifyFixtureHttp(), seed=seed, specs=specs, store=store, now=clock)
    return db, specs, store, r, ok


def test_verifier_matches_clean_run_but_licence_gate_serves_nothing(env):
    """The full technical path passes on recorded bytes (all 14 series of 2026-09 sampled), yet
    REN's redistribution_ok=false keeps served=0: verification is technical, serving is legal."""
    db, specs, store, r, ok = _run(env)
    assert ok and db.run_state(r.run_id) == "verified"
    [(n, passed)] = q(db, "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
                      r.run_id)
    assert (n, passed) == (14, 1)
    # value AND unit compared on balance items; the market CSV exposes no unit surface and the
    # channel has no flag surface at all
    items = q(db, "SELECT series_id, observed_unit, observed_flag FROM verification_item")
    assert len(items) == 14 and all(f is None for _, _, f in items)
    assert {u for _, u, _ in items if u is not None} == {"GWh"}
    assert [u for sid, u, _ in items if "price" in sid] == [None]
    assert q(db, "SELECT redistribution_ok FROM source WHERE name='ren'") == [(0,)]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]
    assert q(db, "SELECT state FROM dataset_run WHERE id=?", r.run_id) == [("verified",)]


def test_archived_evidence_recovers_offline_and_replays(env):
    """Every item's evidence_sha256 reloads from the raw store (integrity checked, no HTTP) and
    decodes to the deciding CSV response's exact bytes + final URL + ACTUAL status (read from
    the archive, not implied); replay_item re-decides each stored comparison offline."""
    db, specs, store, r, ok = _run(env)
    assert ok
    rows = q(db, "SELECT id, series_id, evidence_url, evidence_sha256 FROM verification_item")
    assert len(rows) == 14
    for item_id, sid, url, sha in rows:
        blob = store.load(store.root / "verify-ren" / sha[:2] / sha)  # raises if altered
        key = "market_2026-09" if "price" in sid else "balance_2026-09"
        (rec,) = decode_evidence(blob)
        assert rec == {"url": url, "status": VMANIFEST[key]["status"],
                       "body": vbody(VMANIFEST[key]["file"])}
        assert url == VMANIFEST[key]["url"]
        assert replay_item(db, store, item_id, RenVerifier()) is True


def test_verifier_detects_tampered_value(env):
    """The collected 2026-09 CONSUMO 4442 is tampered to 4443 before writing; the CSV channel
    answers 4442 -> mismatch, failed-verification, still nothing served."""
    db, specs, store, clock = env
    tampered_src = _TamperedFixtureHttp()
    r = run_dataset(db, store, RenSource(periods=("2026-09",)), specs, tampered_src, clock)
    assert r.state == "pending-verification"
    assert not verify_run(db, r.run_id, RenVerifier(), VerifyFixtureHttp(), seed=7, specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "failed-verification"
    bad = q(db, "SELECT series_id, period, expected_text, observed_text, note FROM "
                "verification_item WHERE match=0")
    assert bad == [("ren.electricity_consumption.PT", "2026-09", "4443", "4442",
                    "value differs")]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]


class _TamperedFixtureHttp(FixtureHttp):
    """Source channel where CONSUMO@2026-09 is written as 4443 instead of 4442."""

    def get(self, url, params=None, headers=None, timeout=None):
        r = super().get(url, params=params, headers=headers, timeout=timeout)
        if self.calls and self.calls[-1] == "balance_2026-09":
            from ingest.http import HttpResult
            return HttpResult(status=r.status,
                              body=r.body.replace(b'{"monthly_Accumulation":4442,"type":"CONSUMO"}',
                                                  b'{"monthly_Accumulation":4443,"type":"CONSUMO"}',
                                                  1),
                              url=r.url)
        return r


def test_verifier_detects_tampered_unit_label(env):
    """CSV header '[GWh]' -> '[MWh]': observed_unit 'MWh' != expected 'GWh' -> mismatch."""
    db, specs, store, clock = env
    r = run_dataset(db, store, RenSource(periods=("2026-09",)), specs, FixtureHttp(), clock)
    tampered = vbody(VMANIFEST["balance_2026-09"]["file"]).replace(b"[GWh]", b"[MWh]")
    assert not verify_run(db, r.run_id, RenVerifier(),
                          VerifyFixtureHttp({"balance_2026-09": tampered}), seed=7, specs=specs, store=store, now=clock)
    bad = q(db, "SELECT note FROM verification_item WHERE match=0")
    assert len(bad) == 13 and all("unit differs" in n for (n,) in bad)


class _BothChannels:
    """run_with_refetch shares one Http between collector and verifier: dispatch by host."""

    def __init__(self):
        self.collector = FixtureHttp()
        self.verifier = VerifyFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if "datahub.ren.pt" in url:
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        return self.collector.get(url, params=params, headers=headers, timeout=timeout)


def test_run_with_refetch_verifies_the_registered_verifier(env):
    db, specs, store, clock = env
    v = RenVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, RenSource(periods=("2026-09",)), v, specs,
                           _BothChannels(), now=clock, max_attempts=1)
    assert res.state == "verified"
    [(passed,)] = q(db, "SELECT passed FROM verification")
    assert passed == 1
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]  # licence gate


def test_every_item_replays_from_its_archived_evidence_via_reread(env):
    """Task 21 B-I4: replay re-reads the stored evidence with the verifier's pure reread
    (recorded fixtures, no HTTP) and rejects a stored claim the evidence does not support."""
    db, specs, store, r, ok = _run(env)
    assert ok
    assert assert_replays_from_evidence(db, store, RenVerifier())
