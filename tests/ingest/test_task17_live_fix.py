"""Task 17 live-fix: genuine CONFLICTING canonical duplicates (E-REDES 2026-11-01, the
fall-back day - the portal doubles 01:00/01:15/01:30/01:45 UTC with DIFFERENT values per
copy; controller live-gate raw_fetch id 216 aborted the whole 64k-observation run on this).

Genuine evidence: tests/ingest/fixtures/eredes/nov1_window_json.body (UNMODIFIED raw-store
bytes of raw_fetch id 216, receipt copied verbatim) and nov1_window_csv.body (one fresh
capture of the same day on the verifier channel); MANIFEST.json addendum_2026-11-12_nov1.

Policy under test:
- the SOURCE never arbitrates canonical duplicates and never aborts the day on them: both
  copies are handed unchanged to validate(), whose duplicate_period rule quarantines EVERY
  occurrence (zero duplicates served, no copy chosen, every other cell of history kept);
- the VERIFIER independently marks a stamp repeated in its CSV day file AMBIGUOUS:
  observed_text=None for items at that stamp, no last-row overwrite, no whole-day abort -
  unaffected stamps of 2026-11-01 still verify with exact tokens;
- unchanged fail-closed guards on this fixture: out-of-order records, quoted number tokens,
  HTML answers.
"""
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest

import ingest.verifiers as verifiers
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources import RawResponse
from ingest.sources.eredes import EredesSource
from ingest.validate import validate
from ingest.verifiers import BlindItem, register_verifier
from ingest.verifiers.eredes import EredesVerifier
from ingest.verify import run_with_refetch
from tests.ingest.eredes_fixtures import (
    MANIFEST,
    FixtureHttp,
    all_specs,
    body,
    registry_specs,
)
from tests.ingest.eredes_verifier_fixtures import VerifyFixtureHttp, decode_evidence, vbody

# Named exact samples read from the genuine Nov 1 bytes (both channels carry identical value
# tokens - asserted in test_nov1_fixture...). (period UTC, dgm, pre, total)
NOV1_UNIQUE = [
    ("2026-11-01T00:00:00+00:00", "1113672.0", "165620.0", "1279292.0"),
    ("2026-11-01T00:15:00+00:00", "1091147.0", "168419.0", "1259566.0"),
    ("2026-11-01T02:00:00+00:00", "929708.0", "186487.0", "1116195.0"),
    ("2026-11-01T12:00:00+00:00", "1108745.0", "129761.0", "1238506.0"),
    ("2026-11-01T23:00:00+00:00", "1087493.0", "177831.0", "1265324.0"),
]
# The 4 doubled stamps, BOTH versions in publisher order, values CONFLICTING between copies.
NOV1_DUP_PAIRS = {  # stamp -> [(dgm, pre, total), (dgm, pre, total)]
    "2026-11-01T01:00:00+00:00": [("980304.0", "180706.0", "1161010.0"),
                                  ("1020794.0", "182723.0", "1203517.0")],
    "2026-11-01T01:15:00+00:00": [("961321.0", "186074.0", "1147395.0"),
                                  ("999970.0", "186689.0", "1186659.0")],
    "2026-11-01T01:30:00+00:00": [("947089.0", "184956.0", "1132045.0"),
                                  ("988998.0", "184968.0", "1173966.0")],
    "2026-11-01T01:45:00+00:00": [("946799.0", "185581.0", "1132380.0"),
                                  ("992003.0", "179359.0", "1171362.0")],
}
NOV1_WINDOW = ("2026-11-01T00:00:00+00:00", "2026-11-02T00:00:00+00:00")
SERIES = ("eredes.production_market.PT", "eredes.production_special.PT",
          "eredes.production_total.PT")


def _nov1_source():
    return EredesSource(from_ts=NOV1_WINDOW[0], to_ts=NOV1_WINDOW[1])


def _nov1_responses():
    def rr(name):
        m = MANIFEST["sets"][name]
        return RawResponse(url=m["url"], params=m["params"], status=m["status"],
                           body=body(name))
    return [rr("metadata"), rr("nov1_window_json")]


def _derive_counts():
    """Expected run counts DERIVED from the genuine 97-row bytes, never invented literals."""
    doc = json.loads(body("nov1_window_json"), parse_float=str)
    stamps = [r["datahora"] for r in doc["results"]]
    dup = {s for s, n in Counter(stamps).items() if n > 1}
    return {"rows": len(stamps), "dup_rows": sum(1 for s in stamps if s in dup),
            "unique_stamps": len({s for s in stamps if s not in dup})}


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def _item(sid: str, period: str) -> BlindItem:
    return BlindItem(sid, period, registry_specs()[sid])


# --- fixture evidence ground truth ---------------------------------------------------------

def test_nov1_fixture_is_genuine_conflicting_duplicate_evidence():
    """The fixture itself proves the property the fix exists for; expected counts derive here."""
    d = _derive_counts()
    assert d == {"rows": 97, "dup_rows": 8, "unique_stamps": 89}
    for name in ("nov1_window_json", "nov1_window_csv"):
        m = MANIFEST["sets"][name]
        blob = body(name) if name.endswith("json") else vbody(name)
        assert hashlib.sha256(blob).hexdigest() == m["sha256"] and m["status"] == 200
        assert len(blob) == m["bytes"]
    doc = json.loads(body("nov1_window_json"), parse_float=str)
    by_ts = {}
    for r in doc["results"]:
        by_ts.setdefault(r["datahora"], []).append((r["dgm"], r["pre"], r["total"]))
    for stamp, pair in NOV1_DUP_PAIRS.items():
        assert by_ts[stamp] == list(pair)  # both versions, exact tokens, publisher order
        assert pair[0] != pair[1]  # genuinely CONFLICTING - one copy can never be 'the fix'
    for stamp, dgm, pre, total in NOV1_UNIQUE:
        assert by_ts[stamp] == [(dgm, pre, total)]
    # the two channels carry byte-identical value tokens for every (stamp, occurrence)
    csv_rows = [ln.split(";") for ln in
                vbody("nov1_window_csv").decode("utf-8-sig").split("\r\n") if ln][1:]
    c_by = {}
    for r in csv_rows:
        c_by.setdefault(r[0], []).append((r[6], r[7], r[8]))
    assert c_by == {k: [tuple(t) for t in v] for k, v in by_ts.items()}


# --- source: duplicates flow unchanged to the validator -----------------------------------

def test_source_parses_the_genuine_97_rows_without_raising():
    rows = _nov1_source().parse(all_specs(), _nov1_responses())
    d = _derive_counts()
    assert {sid: len(rs) for sid, rs in rows.items()} == {sid: d["rows"] for sid in SERIES}
    by_key = {sid: sorted((r.period_raw, r.value_raw) for r in rows[sid]) for sid in SERIES}
    for stamp, pair in NOV1_DUP_PAIRS.items():
        for field, values in zip(SERIES, zip(*pair)):
            for v in values:  # BOTH versions reach the validator, publisher order kept
                assert (stamp, v) in by_key[field]


def test_validator_quarantines_every_duplicate_copy_and_keeps_all_other_cells():
    rows = _nov1_source().parse(all_specs(), _nov1_responses())
    d = _derive_counts()
    for sid in SERIES:
        obs, rej = validate(registry_specs()[sid], rows[sid])
        assert len(obs) == d["unique_stamps"]  # zero duplicate copies served
        assert len(rej) == d["dup_rows"] and all(r.reason == "duplicate_period" for r in rej)
        assert {o.period for o in obs}.isdisjoint(NOV1_DUP_PAIRS)  # no copy chosen


def test_nov1_out_of_order_still_fails_closed():
    doc = json.loads(body("nov1_window_json"))
    r0, r1 = doc["results"][5], doc["results"][6]  # both UNIQUE stamps, swapped -> backward
    assert r1["datahora"] > r0["datahora"]
    doc["results"] = doc["results"][:5] + [r1, r0] + doc["results"][7:]
    with pytest.raises(ValueError, match="ascending"):
        _nov1_source().parse(all_specs(), [
            _nov1_responses()[0],
            RawResponse(url=_nov1_responses()[1].url, params=_nov1_responses()[1].params,
                        status=200, body=json.dumps(doc).encode())])


def test_nov1_quoted_number_still_fails_closed():
    tampered = body("nov1_window_json").replace(b'"dgm": 1113672.0', b'"dgm": "1113672.0"', 1)
    assert tampered != body("nov1_window_json")
    with pytest.raises(ValueError, match="number token"):
        _nov1_source().parse(all_specs(), [
            _nov1_responses()[0],
            RawResponse(url=_nov1_responses()[1].url, params=_nov1_responses()[1].params,
                        status=200, body=tampered)])


def test_nov1_html_answer_still_fails_closed():
    with pytest.raises(ValueError, match="markup"):
        _nov1_source().parse(all_specs(), [
            _nov1_responses()[0],
            RawResponse(url=_nov1_responses()[1].url, params=_nov1_responses()[1].params,
                        status=200,
                        body=b"<!DOCTYPE html><html><body>err</body></html>")])


# --- verifier: independent ambiguity sentinel on the genuine CSV ---------------------------

def test_verifier_ambiguous_stamps_not_found_unaffected_still_verified():
    items = ([_item(sid, stamp) for stamp in NOV1_DUP_PAIRS for sid in SERIES]
             + [_item(sid, p) for p, _, _, _ in NOV1_UNIQUE for sid in SERIES]
             + [_item("eredes.production_total.PT", "2026-11-01T23:45:00+00:00")])  # absent
    results = EredesVerifier().check(items, VerifyFixtureHttp())
    by_item = {(r.series_id, r.period): r for r in results}
    # every ambiguous stamp of EVERY series: observed None (never one of the two copies),
    # per-item evidence still archived
    for stamp in NOV1_DUP_PAIRS:
        for sid in SERIES:
            r = by_item[(sid, stamp)]
            assert r.observed_text is None and r.observed_unit == "kWh" and r.evidence
    # explicit ambiguous BlindItem -> not found, no exception
    (ambig,) = EredesVerifier().check(
        [_item("eredes.production_market.PT", "2026-11-01T01:00:00+00:00")],
        VerifyFixtureHttp())
    assert ambig.observed_text is None
    csv_rec, meta_rec = decode_evidence(ambig.evidence)
    assert csv_rec["body"] == vbody("nov1_window_csv") and csv_rec["status"] == 200
    # unaffected unique stamps: exact verbatim tokens on all three series
    for stamp, dgm, pre, total in NOV1_UNIQUE:
        assert by_item[("eredes.production_market.PT", stamp)].observed_text == dgm
        assert by_item[("eredes.production_special.PT", stamp)].observed_text == pre
        assert by_item[("eredes.production_total.PT", stamp)].observed_text == total
    # a stamp simply absent from the day's export: also a mismatch, same path
    assert by_item[("eredes.production_total.PT",
                     "2026-11-01T23:45:00+00:00")].observed_text is None


# --- full registered pipeline --------------------------------------------------------------

class _BothChannels:
    """run_with_refetch shares one Http between collector and verifier: dispatch by path."""

    def __init__(self):
        self.collector = FixtureHttp()
        self.verifier = VerifyFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if "/exports/csv" in url:
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        return self.collector.get(url, params=params, headers=headers, timeout=timeout)


def _clock():
    class Clock:
        t = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)

        def __call__(self):
            self.t += timedelta(seconds=1)
            return self.t
    return Clock()


def test_registered_run_with_refetch_nov1_writes_only_valid_and_duplicate_quarantine(
        db, tmp_path):
    specs = all_specs()
    sync_registry(db, specs)
    store = RawStore(tmp_path / "raw")
    verifier = EredesVerifier()
    register_verifier(verifier)
    d = _derive_counts()
    r = run_with_refetch(db, store, _nov1_source(), verifier, specs, _BothChannels(),
                         max_attempts=1, now=_clock())
    assert r.state == "verified"
    assert r.n_written == d["unique_stamps"] * 3 and r.n_quarantined == d["dup_rows"] * 3
    def q(sql, *a):
        return db.conn.execute(sql, a).fetchall()
    # only valid observations; every duplicate copy quarantined, none chosen
    assert q("SELECT COUNT(*) FROM observation") == [(d["unique_stamps"] * 3,)]
    rows = q("SELECT series_id, raw_period, raw_value, reason FROM quarantine")
    assert len(rows) == d["dup_rows"] * 3
    assert all(reason == "duplicate_period" for *_, reason in rows)
    counts = Counter((sid, p) for sid, p, _, _ in rows)
    assert set(counts) == {(sid, p) for p in NOV1_DUP_PAIRS for sid in SERIES}
    assert all(n == 2 for n in counts.values())  # BOTH copies of each stamp, per series
    assert q("SELECT COUNT(*) FROM observation WHERE period IN "
             "(SELECT raw_period FROM quarantine)") == [(0,)]
    # named unique history kept verbatim in observation.value_text
    exact = {(sid, p): v for p, *vals in NOV1_UNIQUE
             for sid, v in zip(SERIES, vals)}
    periods = [p for p, _, _, _ in NOV1_UNIQUE]
    got = q("SELECT series_id, period, value_text FROM observation WHERE period IN (%s)"
            % ",".join("?" * len(periods)), *periods)
    assert {(sid, p): v for sid, p, v in got} == exact
    # verified -> served; ambiguous stamps never enter served history either
    assert q("SELECT COUNT(*) FROM served_observation") == [(d["unique_stamps"] * 3,)]
    [(n, passed)] = q("SELECT sample_size, passed FROM verification")
    # the one-day CSV carries every stamp: the whole day is compared (free closure, Task 21)
    assert (n, passed) == (d["unique_stamps"] * 3, 1)
    # both channels archived as raw evidence: metadata + records json + the deciding csv
    urls = {u for (u,) in q("SELECT DISTINCT url FROM raw_fetch")}
    assert MANIFEST["sets"]["nov1_window_json"]["url"] in urls
