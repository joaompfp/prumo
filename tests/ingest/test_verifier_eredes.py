"""E-REDES verifier tests - genuine recorded fixtures (tests/ingest/fixtures/eredes/,
2026-11-12): the /exports/csv and metadata of the same one-day window the collector channel
covers. Tamper bytes are labelled synthetic mutations of genuine bytes.
"""
from datetime import datetime, timedelta, timezone

import pytest

import ingest.verifiers as verifiers
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.eredes import EredesSource
from ingest.verifiers import BlindItem, get_verifier, register_verifier
from ingest.verifiers.eredes import EredesVerifier
from ingest.verifiers.independence import assert_verifier_independent
from ingest.verify import replay_item, run_with_refetch, verify_run
from tests.ingest.eredes_fixtures import FixtureHttp, all_specs, body, registry_specs
from tests.ingest.eredes_verifier_fixtures import (
    VMANIFEST,
    VerifyFixtureHttp,
    decode_evidence,
    vbody,
)


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)

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


# Named exact samples, read from the genuine window bytes (window_csv/window_json identical).
CASES = [  # (series, period, value)
    ("eredes.production_market.PT", "2026-11-10T00:00:00+00:00", "925741.0"),
    ("eredes.production_special.PT", "2026-11-10T00:15:00+00:00", "523992.0"),
    ("eredes.production_total.PT", "2026-11-10T06:30:00+00:00", "1340285.0"),
    ("eredes.production_market.PT", "2026-11-10T12:00:00+00:00", "1393848.0"),
    ("eredes.production_total.PT", "2026-11-10T18:45:00+00:00", "1971562.0"),
    ("eredes.production_total.PT", "2026-11-10T23:30:00+00:00", "1551219.0"),
    ("eredes.production_market.PT", "2026-11-10T23:45:00+00:00", "1097652.0"),
]


def test_verifier_reads_every_recorded_case():
    results = EredesVerifier().check([_item(s, p) for s, p, _ in CASES], VerifyFixtureHttp())
    assert [(r.series_id, r.period, r.observed_text, r.observed_unit, r.observed_flag)
            for r in results] == [(s, p, v, "kWh", None) for s, p, v in CASES]
    assert all(r.observed_decimal == "." and r.evidence for r in results)


def test_verifier_caches_one_csv_and_one_metadata_per_check():
    http = VerifyFixtureHttp()
    EredesVerifier().check([_item(s, p) for s, p, _ in CASES], http)
    # Task 17B: one per-SAMPLED-DAY csv; the single-day batch reads its own day csv once,
    # plus one metadata response for the unit labels (order: metadata first is deliberate -
    # labels gate every day file).
    assert http.calls == ["metadata", "window_csv"]


def test_verifier_evidence_envelope_carries_csv_and_metadata():
    (r,) = EredesVerifier().check([_item(*CASES[0][:2])], VerifyFixtureHttp())
    assert r.evidence_url == VMANIFEST["window_csv"]["url"]
    rec_csv, rec_meta = decode_evidence(r.evidence)
    assert rec_csv == {"url": VMANIFEST["window_csv"]["url"],
                       "status": VMANIFEST["window_csv"]["status"],
                       "body": vbody("window_csv")}
    assert rec_meta == {"url": VMANIFEST["metadata"]["url"],
                        "status": VMANIFEST["metadata"]["status"],
                        "body": vbody("metadata")}
    assert rec_csv["status"] == 200 and rec_meta["status"] == 200


def test_verifier_missing_period_is_not_found_and_created_duplicate_is_ambiguous():
    tampered = vbody("window_csv").replace(
        b"2026-11-10T00:15:00+00:00;10", b"2026-11-10T01:15:00+00:00;10", 1)
    results = EredesVerifier().check(
        [_item(*CASES[1][:2]),                       # 00:15: the withdrawn stamp
         _item(CASES[0][0], "2026-11-10T01:15:00+00:00"),  # 01:15: now duplicated
         _item(*CASES[0][:2])],                      # 00:00: unaffected stamp
        VerifyFixtureHttp({"window_csv": tampered}))
    # the withdrawn stamp (00:15) is a mismatch, never a crash...
    assert results[0].observed_text is None
    # ...and the stamp the tamper collided with (01:15) is now AMBIGUOUS: neither copy is
    # served; unaffected stamps of the same day still verify (the day is not aborted)
    assert results[1].observed_text is None
    assert results[2].observed_text == CASES[0][2]


@pytest.mark.parametrize("old,new,match", [
    (b"2026-11-10T00:30:00+00:00;10;11;2026;2026-11-10;00:30",
     b"2026-11-10T00:30:00+00:00;10;11;2026;2026-11-31;00:30", "Gregorian"),  # unreal date
    (b"2026-11-10T00:30:00+00:00;10;11;2026;2026-11-10;00:30",
     b"2026-11-10T00:30:00+00:00;10;11;2026;10-11-2026;00:30", "canonical"),  # wrong shape
    (b"2026-11-10T00:30:00+00:00;10;11;2026;2026-11-10;00:30",
     b"2026-11-10T00:30:00+00:00;11;11;2026;2026-11-10;00:30", "disagree"),   # dia != date
    (b"2026-11-10T00:30:00+00:00;10;11;2026;2026-11-10;00:30",
     b"2026-11-10T00:30:00+00:00;10;11;2026;2026-11-10;0:30", "time"),        # bad HH:MM
])
def test_verifier_aux_wall_time_cells_fail_closed(old, new, match):
    tampered = vbody("window_csv").replace(old, new, 1)
    assert tampered != vbody("window_csv")
    with pytest.raises(ValueError, match=match):
        EredesVerifier().check([_item(*CASES[0][:2])],
                               VerifyFixtureHttp({"window_csv": tampered}))


def test_verifier_absent_row_reports_not_found():
    # synthesize (from genuine bytes) an export that lacks one record entirely
    lines = vbody("window_csv").split(b"\r\n")
    kept = [ln for ln in lines if b"2026-11-10T00:15:00" not in ln]
    tampered = b"\r\n".join(kept)
    (r,) = EredesVerifier().check([_item(*CASES[1][:2])],
                                  VerifyFixtureHttp({"window_csv": tampered}))
    assert r.observed_text is None and r.evidence  # 'not found' is a mismatch, not a guess


def test_verifier_tampered_value_comes_back_verbatim_for_verify_run():
    tampered = vbody("window_csv").replace(b";925741.0;", b";925740.0;", 1)
    (r,) = EredesVerifier().check([_item(*CASES[0][:2])],
                                  VerifyFixtureHttp({"window_csv": tampered}))
    assert r.observed_text == "925740.0"  # detection is verify_run's exact Decimal comparison


@pytest.mark.parametrize("name,old,new,match", [
    ("window_csv",
     b"datahora;dia;mes;ano;date;time;dgm;pre;total",
     b"datahora;dia;mes;ano;date;time;dgm;pre;TOTAL", "header"),
    ("window_csv", b"2026-11-10T00:15:00+00:00", b"2026-11-10 00:15:00+00:00", "canonical"),
    ("window_csv",
     b"2026-11-10T00:15:00+00:00;10;11;2026;2026-11-10;00:15",
     b"2026-11-09T00:15:00+00:00;09;11;2026;2026-11-09;00:15", "outside"),
    ("metadata", b'"label": "Market (kWh)"', b'"label": "Market energy"', "label"),
    ("metadata", b'"dataset_id": "energia-produzida-total-nacional"',
     b'"dataset_id": "other"', "dataset_id"),
])
def test_verifier_channel_drift_fails_closed(name, old, new, match):
    tampered = vbody(name).replace(old, new, 1)
    assert tampered != vbody(name)
    with pytest.raises(ValueError, match=match):
        EredesVerifier().check([_item(*CASES[0][:2])],
                               VerifyFixtureHttp({name: tampered}))


def test_verifier_duplicate_timestamp_is_ambiguous_never_served():
    # a stamp repeated in one day file (the portal genuinely does this across the fall-back
    # boundary, genuine evidence nov1_window_csv): neither copy is served and NO row overwrites
    # another, but the rest of the day still verifies - no whole-day abort.
    tampered = vbody("window_csv").replace(
        b"2026-11-10T00:15:00+00:00;10;11;2026;2026-11-10;00:15",
        b"2026-11-10T00:00:00+00:00;10;11;2026;2026-11-10;00:00", 1)
    results = EredesVerifier().check([_item(*CASES[0][:2]), _item(*CASES[2][:2])],
                                     VerifyFixtureHttp({"window_csv": tampered}))
    assert results[0].period == "2026-11-10T00:00:00+00:00" and results[0].observed_text is None
    assert results[1].observed_text == CASES[2][2]  # unaffected unique stamp, exact token


def test_verifier_html_page_raises():
    with pytest.raises(ValueError, match="markup"):
        EredesVerifier().check([_item(*CASES[0][:2])], VerifyFixtureHttp(
            {"window_csv": b"<!DOCTYPE html><html><body>err</body></html>"}))


def test_verifier_non_2xx_raises():
    class Denied(VerifyFixtureHttp):
        def get(self, url, params=None, headers=None, timeout=None):
            from ingest.http import HttpResult
            return HttpResult(status=503, body=b'{"error":"down"}', url=url)

    with pytest.raises(ValueError, match="HTTP 503"):
        EredesVerifier().check([_item(*CASES[0][:2])], Denied())


def test_verifier_registers_and_passes_allowlist():
    v = EredesVerifier()
    register_verifier(v)  # the static independence allowlist runs here
    assert get_verifier("eredes") is v


def test_verifier_registers_even_in_same_process_as_the_source():
    import ingest.sources.eredes  # noqa: F401  (loaded: the static allowlist must still pass)
    register_verifier(EredesVerifier())


def test_subprocess_independence():
    assert_verifier_independent("ingest.verifiers.eredes",
                                "tests.ingest.eredes_verifier_entry:run",
                                source_name="eredes",
                                blocked_prefixes=("collectors", "ingest.flags",
                                                  "ingest.sources"))


# --- through the pipeline -----------------------------------------------------------------------

def _window_source():
    return EredesSource(from_ts="2026-11-10T00:00:00+00:00", to_ts="2026-11-11T00:00:00+00:00")


@pytest.fixture
def env(db, tmp_path):
    specs = all_specs()
    sync_registry(db, specs)
    return db, specs, RawStore(tmp_path / "raw"), Clock()


def _run(env, seed=7):
    db, specs, store, clock = env
    r = run_dataset(db, store, _window_source(), specs, FixtureHttp(), clock)
    assert r.state == "pending-verification" and r.n_written == 288
    ok = verify_run(db, r.run_id, EredesVerifier(), VerifyFixtureHttp(), seed=seed, size=50,
                    specs=specs, store=store, now=clock)
    return db, specs, store, r, ok


def test_verified_run_is_served_under_cc_by(env):
    """CC BY 4.0 + redistribution_ok=true: a verified E-REDES run IS served (unlike REN)."""
    db, specs, store, r, ok = _run(env)
    assert ok and db.run_state(r.run_id) == "verified"
    [(n, passed)] = q(db, "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
                      r.run_id)
    assert (n, passed) == (50, 1)
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(288,)]
    items = q(db, "SELECT series_id, period, observed_unit, observed_flag FROM "
                  "verification_item")
    assert len(items) == 50 and all(u == "kWh" and f is None for _, _, u, f in items)
    # expected/observed exact tokens stored item-side, decimal '.'
    row = q(db, "SELECT expected_text, observed_text, expected_decimal, observed_decimal FROM "
                "verification_item WHERE period='2026-11-10T23:45:00+00:00' AND "
                "series_id='eredes.production_market.PT'")
    assert row == [("1097652.0", "1097652.0", ".", ".")]


def test_archived_evidence_recovers_offline_and_replays(env):
    """Every item's evidence_sha256 reloads from the raw store (integrity-checked, no HTTP) and
    decodes to the deciding CSV + metadata responses' exact bytes/urls/statuses; replay_item
    re-decides each stored comparison offline; served values equal the CSV tokens verbatim."""
    db, specs, store, r, ok = _run(env)
    assert ok
    rows = q(db, "SELECT id, evidence_url, evidence_sha256 FROM verification_item")
    assert len(rows) == 50
    for item_id, url, sha in rows:
        blob = store.load(store.root / "verify-eredes" / sha[:2] / sha)  # raises if altered
        rec_csv, rec_meta = decode_evidence(blob)
        assert url == VMANIFEST["window_csv"]["url"] == rec_csv["url"]
        assert rec_csv["body"] == vbody("window_csv")
        assert rec_meta["body"] == vbody("metadata")
        assert replay_item(db, store, item_id) is True
    # offline unit+value recovery proof: values/units of every served series come from the
    # archived evidence alone
    assert q(db, "SELECT value_text FROM served_observation WHERE series_id="
                 "'eredes.production_total.PT' AND period='2026-11-10T23:30:00+00:00'") == \
        [("1551219.0",)]


def test_verifier_detects_tampered_value(env):
    """Collected dgm@2026-11-10T23:45Z 1097652.0 is tampered to 1097653.0 before writing; the
    CSV channel answers 1097652.0 -> mismatch, failed-verification, nothing served. (23:45 is
    the series' latest period: draw_sample always includes it.)"""
    db, specs, store, clock = env
    tampered = body("window_json").replace(b'"dgm": 1097652.0', b'"dgm": 1097653.0', 1)
    r = run_dataset(db, store, _window_source(), specs,
                    FixtureHttp({"window_json": tampered}), clock)
    assert r.state == "pending-verification"
    assert not verify_run(db, r.run_id, EredesVerifier(), VerifyFixtureHttp(), seed=7, size=50,
                          specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "failed-verification"
    bad = q(db, "SELECT series_id, period, expected_text, observed_text, note FROM "
                "verification_item WHERE match=0")
    assert bad == [("eredes.production_market.PT", "2026-11-10T23:45:00+00:00", "1097653.0",
                    "1097652.0", "value differs")]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]


def test_verifier_detects_tampered_unit_label(env):
    """Metadata label 'Market (kWh)' -> 'Market (MWh)': observed_unit 'MWh' != expected 'kWh'."""
    db, specs, store, clock = env
    r = run_dataset(db, store, _window_source(), specs, FixtureHttp(), clock)
    tampered = vbody("metadata").replace(b'"label": "Market (kWh)"',
                                                            b'"label": "Market (MWh)"', 1)
    assert not verify_run(db, r.run_id, EredesVerifier(),
                          VerifyFixtureHttp({"metadata": tampered}), seed=7, size=50,
                          specs=specs, store=store, now=clock)
    bad = q(db, "SELECT series_id, note FROM verification_item WHERE match=0")
    assert bad and all("unit differs" in n for _, n in bad)
    assert all(sid.startswith("eredes.production_market") for sid, _ in bad)


class _BothChannels:
    """run_with_refetch shares one Http: dispatch by whether the request carries an
    exports/csv path (verifier) or is the records API (collector)."""

    def __init__(self):
        self.collector = FixtureHttp()
        self.verifier = VerifyFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if "/exports/csv" in url:
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        if (params or {}).get("lang") == "pt" and (params or {}).get("timezone") == "UTC":
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        # the metadata URL is shared by both channels - the recorded bytes are identical
        if "/datasets/energia-produzida-total-nacional" in url and params is None:
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        return self.collector.get(url, params=params, headers=headers, timeout=timeout)


def test_run_with_refetch_verifies_the_registered_verifier(env):
    db, specs, store, clock = env
    v = EredesVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, _window_source(), v, specs, _BothChannels(), size=50,
                           now=clock, max_attempts=1)
    assert res.state == "verified"
    [(passed,)] = q(db, "SELECT passed FROM verification")
    assert passed == 1
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(288,)]


# --- genuine WEST-summer window (C1 regression, 2026-04-01 UTC day) ------------------------------

# Named exact samples from the genuine summer_window_csv (byte-decimal-identical to the JSON
# channel at archiving time; aux cells are Lisbon wall time and deliberately NOT echoed here).
SUMMER_CASES = [  # (series, period, value)
    ("eredes.production_market.PT", "2026-04-01T00:00:00+00:00", "945304.0"),
    ("eredes.production_special.PT", "2026-04-01T01:00:00+00:00", "406955.266"),
    ("eredes.production_total.PT", "2026-04-01T12:00:00+00:00", "1423799.417"),
    ("eredes.production_market.PT", "2026-04-01T22:45:00+00:00", "1278743.0"),
    ("eredes.production_total.PT", "2026-04-01T23:45:00+00:00", "1369057.51"),
]


def _summer_source():
    return EredesSource(from_ts="2026-04-01T00:00:00+00:00", to_ts="2026-04-02T00:00:00+00:00")


def test_verifier_reads_summer_cases_from_the_wall_time_export():
    results = EredesVerifier().check([_item(s, p) for s, p, _ in SUMMER_CASES],
                                     VerifyFixtureHttp())
    assert [(r.series_id, r.period, r.observed_text, r.observed_unit, r.observed_flag)
            for r in results] == [(s, p, v, "kWh", None) for s, p, v in SUMMER_CASES]
    assert all(r.evidence for r in results)


def test_run_with_refetch_verifies_and_serves_the_summer_window(env):
    """C1 end-to-end regression: the genuine April archive (rejected at the live gate by the
    withdrawn guard) runs the REGISTERED pipeline to verified, serves 288 obs under CC BY 4.0,
    and every sampled item's evidence replays offline from the raw store."""
    db, specs, store, clock = env
    v = EredesVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, _summer_source(), v, specs, _BothChannels(), size=50,
                           now=clock, max_attempts=1)
    assert res.state == "verified"
    [(passed,)] = q(db, "SELECT passed FROM verification")
    assert passed == 1
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(288,)]
    assert q(db, "SELECT value_text FROM served_observation WHERE series_id="
                 "'eredes.production_total.PT' AND period='2026-04-01T23:45:00+00:00'") == \
        [("1369057.51",)]
    rows = q(db, "SELECT id, evidence_url, evidence_sha256 FROM verification_item")
    for item_id, url, sha in rows:
        blob = store.load(store.root / "verify-eredes" / sha[:2] / sha)  # raises if altered
        rec_csv, rec_meta = decode_evidence(blob)
        assert url == VMANIFEST["summer_window_csv"]["url"] == rec_csv["url"]
        assert rec_csv["body"] == vbody("summer_window_csv")
        assert rec_meta["body"] == vbody("metadata")
        assert replay_item(db, store, item_id) is True
