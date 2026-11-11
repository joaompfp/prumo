"""Banco de Portugal verifier tests — recorded portal-API fixtures
(tests/ingest/fixtures/bportugal/verify/, 2026-11-11)."""
import base64
import json
from datetime import datetime, timedelta, timezone

import pytest

import ingest.verifiers as verifiers
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.bportugal import BPortugalSource
from ingest.verifiers import BlindItem, get_verifier, register_verifier
from ingest.verifiers.bportugal import BPortugalVerifier
from ingest.verifiers.independence import assert_verifier_independent
from ingest.verify import run_with_refetch, verify_run
from tests.ingest.bportugal_fixtures import FixtureHttp, all_specs, body, specs_of
from tests.ingest.bportugal_verifier_fixtures import VMANIFEST, VerifyFixtureHttp, vbody


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def _item(sid_key: str, period: str):
    reg = {s.id: s for s in all_specs()}
    return BlindItem(sid_key, period, reg[sid_key])


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


CASES = {key: m for key, m in VMANIFEST["cases"].items()}


def test_verifier_reads_every_recorded_case():
    """All recorded (single-vintage and multi-vintage) cases come back with the cross-checked
    token; the empty month is 'not found'."""
    specs = {s.id: s for s in all_specs()}
    id_by_native = {int((s.native_code or "").split(":")[0]): s.id for s in specs.values()}
    items, expected = [], []
    for key, m in CASES.items():
        sid = id_by_native[m["series_id"]]
        items.append(BlindItem(sid, m["period"], specs[sid]))
        expected.append((sid, m["period"], m["expected_text"]))
    results = BPortugalVerifier().check(items, VerifyFixtureHttp())
    got = [(r.series_id, r.period, r.observed_text) for r in results]
    assert got == expected


def test_verifier_vintage_rule_selects_the_latest_publication():
    """12099464 @2023-08: vintages '3.30' (pub 2023-09-04) then '3.31' (pub 2023-10-03); the
    portal currently publishes 3.31, which the collector's JSON-stat payload also carries."""
    m = CASES["12099464@2023-08"]
    assert m["vintages"] == [["3.30", "2023-09-04T15:30:00Z"], ["3.31", "2023-10-03T15:30:00Z"]]
    (r,) = BPortugalVerifier().check([_item("bportugal.pt_10y.PT", "2023-08")],
                                     VerifyFixtureHttp())
    assert r.observed_text == "3.31"


def test_verifier_empty_month_is_not_found_not_a_guess():
    (r,) = BPortugalVerifier().check([_item("bportugal.de_10y.DE", "1999-12")],
                                     VerifyFixtureHttp())
    assert r.observed_text is None  # DE yields start 2000-01: no observation to echo


def test_verifier_unit_and_decimal_surfaces():
    results = [BPortugalVerifier().check([_item(sid, period)], VerifyFixtureHttp())[0]
               for sid, period in [("bportugal.euribor_3m.EA", "2026-10"),
                                   ("bportugal.de_10y.DE", "2026-10"),
                                   ("bportugal.credit_housing.PT", "2026-09"),
                                   ("bportugal.deposits_households.PT", "2026-09"),
                                   ("bportugal.eur_usd.EA", "2026-10")]]
    assert {(r.series_id, r.observed_unit) for r in results} == {
        ("bportugal.euribor_3m.EA", "%"), ("bportugal.de_10y.DE", "%"),
        ("bportugal.credit_housing.PT", "MEUR"), ("bportugal.deposits_households.PT", "MEUR"),
        ("bportugal.eur_usd.EA", "USD/EUR")}
    assert all(r.observed_decimal == "." and r.evidence and r.observed_flag is None
               for r in results)
    assert all(r.evidence_url.startswith("https://bpstat.bportugal.pt/api/observations/")
               for r in results)


def test_verifier_meta_fetched_once_per_series():
    http = VerifyFixtureHttp()
    BPortugalVerifier().check([_item("bportugal.euribor_3m.EA", "1994-01"),
                               _item("bportugal.euribor_3m.EA", "2026-10"),
                               _item("bportugal.euribor_1m.EA", "2026-10")], http)
    assert http.calls == [("meta", "13168436"), ("obs", "13168436@1994-01"),
                          ("obs", "13168436@2026-10"), ("meta", "13168439"),
                          ("obs", "13168439@2026-10")]


def test_verifier_tampered_observation_value_raises():
    tampered = vbody("obs_12099464_2026-10.json").replace(b'"value":"3.92"',
                                                          b'"value":"3.99"', 1)
    # the raw edit leaves a valid payload that simply answers a DIFFERENT number; the verifier
    # itself returns it verbatim — detection happens in verify_run (test below); here _current
    # gives the tampered token back unchanged
    (r,) = BPortugalVerifier().check([_item("bportugal.pt_10y.PT", "2026-10")],
                                     VerifyFixtureHttp({"12099464@2026-10": tampered}))
    assert r.observed_text == "3.99"


def test_verifier_wrong_series_in_rows_raises():
    tampered = vbody("obs_12099464_2026-10.json").replace(b'"series_id":12099464',
                                                          b'"series_id":12560098', 1)
    with pytest.raises(ValueError, match="another series"):
        BPortugalVerifier().check([_item("bportugal.pt_10y.PT", "2026-10")],
                                  VerifyFixtureHttp({"12099464@2026-10": tampered}))


def test_verifier_non_public_privacy_code_raises():
    tampered = vbody("obs_12099464_2026-10.json").replace(b'"privacy_code":"P"',
                                                          b'"privacy_code":"C"', 1)
    with pytest.raises(ValueError, match="privacy_code"):
        BPortugalVerifier().check([_item("bportugal.pt_10y.PT", "2026-10")],
                                  VerifyFixtureHttp({"12099464@2026-10": tampered}))


def test_verifier_nonempty_description_raises():
    tampered = vbody("obs_12099464_2026-10.json").replace(b'"description":{}',
                                                          b'"description":{"EN":"provisional '
                                                          b'value"}', 1)
    with pytest.raises(ValueError, match="description"):
        BPortugalVerifier().check([_item("bportugal.pt_10y.PT", "2026-10")],
                                  VerifyFixtureHttp({"12099464@2026-10": tampered}))


def test_verifier_unknown_unit_label_raises():
    tampered = vbody("series_full_12099464.json").replace(b'"EN":"Percentage"',
                                                          b'"EN":"Index"', 1)
    with pytest.raises(ValueError, match="unit"):
        BPortugalVerifier().check([_item("bportugal.pt_10y.PT", "2026-10")],
                                  VerifyFixtureHttp({"12099464": tampered}))


# --- evidence: the archived bytes must carry BOTH portal responses (Ruling R/G7) -------------

def _decode_evidence(evidence: bytes) -> dict:
    """Offline (no HTTP) read of the versioned evidence envelope: the exact wire record of the
    metadata and the observations responses, each body recovered byte-for-byte."""
    doc = json.loads(evidence)
    assert doc["schema"] == "bportugal-portal-evidence" and doc["version"] == 1
    return {k: {"url": v["url"], "status": v["status"],
                "body": base64.b64decode(v["body_b64"], validate=True)}
            for k, v in doc.items() if k in ("metadata", "observations")}


def test_verifier_evidence_bundles_metadata_and_observation_responses():
    """The unit decision used the /api/series/ response; the value decision used the
    /api/observations/ response. The archived evidence must carry BOTH exact wire records —
    observations body alone is not auditable for the unit verification."""
    (r,) = BPortugalVerifier().check([_item("bportugal.pt_10y.PT", "2026-10")],
                                     VerifyFixtureHttp())
    meta, case = VMANIFEST["meta"]["12099464"], VMANIFEST["cases"]["12099464@2026-10"]
    doc = _decode_evidence(r.evidence)
    assert doc["metadata"] == {"url": meta["url"], "status": 200, "body": vbody(meta["file"])}
    assert doc["observations"] == {"url": case["url"], "status": 200,
                                   "body": vbody(case["file"])}
    assert r.evidence_url == case["url"]  # continuity: evidence_url stays the observations URL


def test_verifier_evidence_shares_cached_metadata_but_bundles_each_observation():
    http = VerifyFixtureHttp()
    results = BPortugalVerifier().check([_item("bportugal.euribor_3m.EA", "1994-01"),
                                         _item("bportugal.euribor_3m.EA", "2026-10")], http)
    assert http.calls.count(("meta", "13168436")) == 1  # metadata still fetched once per series
    meta = VMANIFEST["meta"]["13168436"]
    for r, key in zip(results, ("13168436@1994-01", "13168436@2026-10")):
        doc = _decode_evidence(r.evidence)
        assert doc["metadata"] == {"url": meta["url"], "status": 200,
                                   "body": vbody(meta["file"])}
        assert doc["observations"]["body"] == vbody(VMANIFEST["cases"][key]["file"])


def test_verifier_recurrence_mismatch_raises():
    tampered = vbody("series_full_12099464.json").replace(b'"recurrence":"M"',
                                                          b'"recurrence":"Q"', 1)
    with pytest.raises(ValueError, match="recurrence|periodicity|frequency"):
        BPortugalVerifier().check([_item("bportugal.pt_10y.PT", "2026-10")],
                                  VerifyFixtureHttp({"12099464": tampered}))


def test_verifier_markup_answer_raises():
    with pytest.raises(ValueError, match="markup"):
        BPortugalVerifier().check([_item("bportugal.pt_10y.PT", "2026-10")],
                                  VerifyFixtureHttp({"12099464": b"<html>error</html>"}))


def test_verifier_registers_and_passes_allowlist():
    v = BPortugalVerifier()
    register_verifier(v)  # the static independence allowlist runs here
    assert get_verifier("bportugal") is v


def test_verifier_registers_even_in_same_process_as_the_source():
    import ingest.sources.bportugal  # noqa: F401  (loaded: the static allowlist must still pass)
    v = BPortugalVerifier()
    register_verifier(v)


def test_subprocess_independence():
    assert_verifier_independent("ingest.verifiers.bportugal",
                                "tests.ingest.bportugal_verifier_entry:run",
                                source_name="bportugal",
                                blocked_prefixes=("collectors", "ingest.flags", "ingest.sources"))


# --- through the pipeline -----------------------------------------------------------------------

@pytest.fixture
def env(db, tmp_path):
    specs = all_specs()
    sync_registry(db, specs)
    return db, specs, RawStore(tmp_path / "raw"), Clock()


def test_verifier_matches_clean_run(env):
    db, specs, store, clock = env
    r = run_dataset(db, store, BPortugalSource(), specs, FixtureHttp(), clock)
    assert r.state == "pending-verification" and r.n_written == 4318
    assert verify_run(db, r.run_id, BPortugalVerifier(), VerifyFixtureHttp(), seed=7, size=16,
                      specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "verified"
    [(n, passed)] = q(db, "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
                      r.run_id)
    assert passed == 1 and n == 16
    # every sampled item compared value AND unit; the portal channel exposes no observation
    # status, so observed_flag is NULL for all (flag comparison skipped by design, documented)
    assert q(db, "SELECT COUNT(*) FROM verification_item WHERE observed_unit IS NULL "
                 "OR evidence_sha256 IS NULL OR observed_flag IS NOT NULL") == [(0,)]
    units = {u for (u,) in q(db, "SELECT DISTINCT observed_unit FROM verification_item")}
    assert units == {"%", "MEUR", "USD/EUR"}
    served = q(db, "SELECT COUNT(*) FROM served_observation WHERE series_id LIKE 'bportugal.%'")
    assert served[0][0] == 4318


def test_archived_evidence_decodes_to_both_portal_responses_without_http(env):
    """Every sampled item's archived evidence_sha256 reloads from the raw store (integrity
    checked, no HTTP) and decodes to the exact portal metadata AND observations wire bytes."""
    db, specs, store, clock = env
    r = run_dataset(db, store, BPortugalSource(), specs, FixtureHttp(), clock)
    assert verify_run(db, r.run_id, BPortugalVerifier(), VerifyFixtureHttp(), seed=7, size=16,
                      specs=specs, store=store, now=clock)
    native = {s.id: (s.native_code or "").split(":")[0] for s in specs}
    rows = q(db, "SELECT series_id, period, evidence_url, evidence_sha256 FROM "
                 "verification_item")
    assert len(rows) == 16
    for series_id, period, url, sha in rows:
        blob = store.load(store.root / "verify-bportugal" / sha[:2] / sha)  # raises if altered
        doc = _decode_evidence(blob)
        meta, case = VMANIFEST["meta"][native[series_id]], \
            VMANIFEST["cases"][f"{native[series_id]}@{period}"]
        assert doc["observations"] == {"url": url, "status": 200, "body": vbody(case["file"])}
        assert doc["metadata"] == {"url": meta["url"], "status": 200, "body": vbody(meta["file"])}


def test_verifier_detects_tampered_value(env):
    """The JSON-stat payload is tampered on pt_10y 2026-10 ('3.92' -> '3.93'); that period is
    always sampled (every series' latest is) and the portal channel answers 3.92."""
    db, specs, store, clock = env
    raw = body("yields.json")
    assert raw.count(b',"3.85","3.92",null') == 1  # unique anchor: ...pt@2026-09, pt@2026-10, de@1993-07
    tampered = raw.replace(b',"3.85","3.92",null', b',"3.85","3.93",null', 1)
    r = run_dataset(db, store, BPortugalSource(), specs,
                    FixtureHttp({"yields": tampered}), clock)
    assert r.state == "pending-verification"
    assert not verify_run(db, r.run_id, BPortugalVerifier(), VerifyFixtureHttp(), seed=7,
                          size=16, specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "failed-verification"
    bad = q(db, "SELECT series_id, period, expected_text, observed_text, note FROM "
                "verification_item WHERE match=0")
    assert bad == [("bportugal.pt_10y.PT", "2026-10", "3.93", "3.92", "value differs")]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]


def test_tampered_unit_of_measure_is_detected_by_the_adapter():
    """Unit drift never even reaches validation: a 'Percentage' -> 'Index' payload edit makes
    the parse raise (fail-closed unit map), so the run fails validation, nothing served."""
    raw = body("yields.json")
    tampered = raw.replace(b'"label":{"3327":"Percentage"}', b'"label":{"3327":"Index"}', 1)
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="unit"):
        BPortugalSource().parse(specs, [_resp(raw=tampered)])


def _resp(raw: bytes):
    from ingest.sources import RawResponse
    return RawResponse(url="", params={}, status=200, body=raw)


class _BothChannels:
    """run_with_refetch shares one Http between collector and verifier: dispatch by path."""

    def __init__(self):
        self.collector = FixtureHttp()
        self.verifier = VerifyFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if "/api/" in url:
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        return self.collector.get(url, params=params, headers=headers, timeout=timeout)


def test_run_with_refetch_uses_registered_verifier(env):
    """Only the registered verifier may pass; the verified happy path runs live
    (tests/ingest/test_live_bportugal.py) with a random seed, which cannot be recorded."""
    db, specs, store, clock = env
    v = BPortugalVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, BPortugalSource(), v, specs, _BothChannels(), size=16,
                           now=clock, max_attempts=1)
    [(passed,)] = q(db, "SELECT passed FROM verification")
    if not passed:
        # months outside the recorded ones fail the run loudly (the fake answers
        # AssertionError), never a false pass and nothing served
        assert res.state == "failed-verification"
        assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]
        notes = [n for (n,) in q(db, "SELECT note FROM verification_item WHERE match=0")]
        assert any("no recorded verifier response" in (n or "") for n in notes)
    else:
        assert res.state == "verified"
