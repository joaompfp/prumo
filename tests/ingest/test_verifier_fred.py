"""FRED independent verifier tests — recorded server-rendered /data/<CODE> table pages
(tests/ingest/fixtures/fred/table-<CODE>.html, fetched 2026-11-12, sha256-pinned byte copies
of the Task-14 preflight originals in MANIFEST.json). Mutations are built IN-TEST only, never
stored as genuine evidence. The verifier reads no other channel: API/CSV/landing page unused.
"""
import base64
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import pytest

import ingest.verifiers as verifiers
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.fred import FredSource
from ingest.verifiers import BlindItem, get_verifier, register_verifier
from ingest.verifiers.fred import FredVerifier, read_table_page
from ingest.verifiers.independence import assert_verifier_independent
from ingest.verify import replay_item, run_with_refetch, verify_run
from tests.ingest.fred_fixtures import (
    SENTINEL_KEY,
    FixtureHttp,
    active_specs,
    body,
    entry,
    registry_specs,
    table_values,
)
from tests.ingest.fred_verifier_fixtures import TableFixtureHttp
from tests.ingest.replay_helpers import assert_replays_from_evidence

_ALUM = "fred.aluminum.WORLD"

# (series id, period) named pins; expectations are re-derived from the ARCHIVED table bytes
# via the test-only extractor — the exact publisher cell token, trailing-zero padding kept.
PINS = [
    ("fred.aluminum.WORLD", "1992-01"),
    ("fred.aluminum.WORLD", "2026-09"),
    ("fred.brent_oil.WORLD", "1992-01"),
    ("fred.brent_oil.WORLD", "2026-09"),
    ("fred.coffee.WORLD", "1992-01"),
    ("fred.coffee.WORLD", "2026-09"),
    ("fred.cotton.WORLD", "1992-01"),
    ("fred.commodity_soybean.WORLD", "2026-09"),
    ("fred.commodity_zinc.WORLD", "2026-09"),
]


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 12, 13, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


def _item(sid: str, period: str) -> BlindItem:
    return BlindItem(sid, period, registry_specs()[sid])


def _alum(period: str, **kw):
    (r,) = FredVerifier().check([_item(_ALUM, period)], TableFixtureHttp(**kw))
    return r


def _mutate(old: bytes, new: bytes, file: str = "table-PALUMUSDM.html") -> bytes:
    """In-test mutation of a genuine archived page; the anchor must occur exactly once."""
    raw = body(file)
    assert raw.count(old) == 1, f"anchor not unique in {file}: {old[:64]!r}"
    return raw.replace(old, new, 1)


def _obs_row_re(date: str) -> bytes:
    return (rb'<tr>\s*<th scope="row" class="pe-5">' + date.encode() +
            rb'</th>\s*<td class="pe-5">[^<]*</td>\s*</tr>')


# ----------------------------------------------------------------------- happy path / pins

def test_named_pins_read_the_exact_publisher_cell_tokens():
    for sid, period in PINS:
        (r,) = FredVerifier().check([_item(sid, period)], TableFixtureHttp())
        code = registry_specs()[sid].native_code
        expected = table_values(code)[f"{period}-01"]
        assert expected and r.observed_text == expected  # exact token, padding preserved
        assert r.observed_unit == registry_specs()[sid].unit  # read from the HTML metadata
        assert r.observed_decimal == "." and r.observed_flag is None and r.evidence
        assert r.evidence_url == entry(f"table-{code}.html")["url"]


def test_all_12_series_table_pages_cover_first_and_last_month():
    specs = active_specs()
    assert len(specs) == 12  # the active registry set, not a hardcoded mapping
    items = []
    for s in sorted(specs, key=lambda s: s.id):
        table = table_values(s.native_code)
        first, last = min(table)[:7], max(table)[:7]
        assert (first, last) == ("1992-01", "2026-09")
        items += [_item(s.id, first), _item(s.id, last)]
    http = TableFixtureHttp()
    results = FredVerifier().check(items, http)
    assert len(results) == 24
    assert len(http.calls) == 12  # ONE /data/<code> fetch per series per check()
    for item, r in zip(items, results):
        assert r.observed_text == table_values(item.spec.native_code)[f"{item.period}-01"]
        assert r.observed_unit == item.spec.unit


def test_one_page_fetch_per_series_per_check():
    http = TableFixtureHttp()
    FredVerifier().check([_item(_ALUM, "1992-01"), _item(_ALUM, "2000-06"),
                          _item(_ALUM, "2026-09"), _item("fred.brent_oil.WORLD", "2026-09")],
                         http)
    assert http.calls == ["PALUMUSDM", "POILBREUSDM"]


def test_missing_period_is_honest_not_found():
    # every active series' pre-1992 months are genuinely absent from the table page
    assert _alum("1991-12").observed_text is None
    # an interior row removed IN-TEST: the period is absent, never invented
    tampered, n = re.subn(_obs_row_re("1993-06-01"), b"", body("table-PALUMUSDM.html"))
    assert n == 1
    (r,) = FredVerifier().check([_item(_ALUM, "1993-06")],
                                TableFixtureHttp({"table-PALUMUSDM.html": tampered}))
    assert r.observed_text is None


def test_missing_marker_cell_is_honest_not_found():
    token = table_values("PALUMUSDM")["1992-01-01"].encode()
    tampered = _mutate(b'<td class="pe-5">' + token + b"</td>", b'<td class="pe-5">.</td>')
    (r,) = FredVerifier().check([_item(_ALUM, "1992-01")],
                                TableFixtureHttp({"table-PALUMUSDM.html": tampered}))
    assert r.observed_text is None  # '.' is the only reviewed missing marker: proved missing


# ----------------------------------------------------------------------- fail-closed drift

def test_non_2xx_raises():
    with pytest.raises(ValueError, match="HTTP 503"):
        _alum("1992-01", status={"PALUMUSDM": 503})


def test_error_page_without_the_reviewed_tables_raises():
    page = b"<!DOCTYPE html><html><body><h1>Page not found</h1></body></html>"
    with pytest.raises(ValueError, match="metadata table"):
        _alum("1992-01", override={"table-PALUMUSDM.html": page})


def test_duplicate_metadata_table_raises():
    raw = body("table-PALUMUSDM.html")
    start = raw.index(b'<table aria-label="metadata - ')
    end = raw.index(b"</table>", start) + len(b"</table>")
    with pytest.raises(ValueError, match=r"\b2 metadata tables"):
        _alum("1992-01", override={"table-PALUMUSDM.html": raw + b"\n" + raw[start:end]})


def test_duplicate_observations_table_raises():
    extra = (b'<table id="data-table-observations" aria-labelledby="data-table-title">'
             b'<thead><tr><th scope="col">DATE</th><th scope="col">VALUE</th></tr></thead>'
             b'<tbody><tr><th scope="row">2026-10-01</th><td>1.0</td></tr></tbody></table>')
    page = body("table-PALUMUSDM.html") + b"\n" + extra
    with pytest.raises(ValueError, match=r"\b2 observations tables"):
        _alum("1992-01", override={"table-PALUMUSDM.html": page})


def test_wrong_series_id_raises():
    tampered = _mutate(b"<td>PALUMUSDM</td>", b"<td>PCOPPUSDM</td>")
    with pytest.raises(ValueError, match="Series ID.*asked"):
        _alum("1992-01", override={"table-PALUMUSDM.html": tampered})


def test_unknown_or_drifted_units_raise():
    tampered = _mutate(b"<td>U.S. Dollars per Metric Ton</td>", b"<td>Index</td>")
    with pytest.raises(ValueError, match="Units.*registry"):
        _alum("1992-01", override={"table-PALUMUSDM.html": tampered})
    # the unit is ASSERTED against the registry, never copied from it: a wrong registry label
    # against the genuine page raises too
    spec = registry_specs()[_ALUM].model_copy(update={"unit": "USD"})
    with pytest.raises(ValueError, match="!= registry unit"):
        FredVerifier().check([BlindItem(_ALUM, "1992-01", spec)], TableFixtureHttp())


def test_unknown_frequency_and_seasonal_adjustment_raise():
    tampered = _mutate(b"<td>Monthly</td>", b"<td>Quarterly</td>")
    with pytest.raises(ValueError, match="Frequency"):
        _alum("1992-01", override={"table-PALUMUSDM.html": tampered})
    tampered = _mutate(b"<td>Not Seasonally Adjusted</td>", b"<td>Seasonally Adjusted</td>")
    with pytest.raises(ValueError, match="Seasonal Adjustment"):
        _alum("1992-01", override={"table-PALUMUSDM.html": tampered})


def test_source_release_and_title_concept_drift_raise():
    tampered = _mutate(b"<td>International Monetary Fund</td>", b"<td>FRED</td>")
    with pytest.raises(ValueError, match="Source"):
        _alum("1992-01", override={"table-PALUMUSDM.html": tampered})
    tampered = _mutate(b"<td>Primary Commodity Prices (Not a Press Release)</td>",
                       b"<td>Other Release</td>")
    with pytest.raises(ValueError, match="Release"):
        _alum("1992-01", override={"table-PALUMUSDM.html": tampered})
    tampered = _mutate(b"<td>Global price of Aluminum</td>", b"<td>Aluminum</td>")
    with pytest.raises(ValueError, match="Title"):
        _alum("1992-01", override={"table-PALUMUSDM.html": tampered})


def test_duplicate_period_raises():
    raw = body("table-PALUMUSDM.html")
    row = re.search(_obs_row_re("1992-01-01"), raw)
    assert row
    with pytest.raises(ValueError, match="duplicate period"):
        _alum("2000-06", override={"table-PALUMUSDM.html":
                                   raw.replace(row.group(0), row.group(0) + row.group(0), 1)})


def test_extra_status_column_and_header_drift_raise():
    token = table_values("PALUMUSDM")["1992-02-01"].encode()
    tampered = _mutate(b'<td class="pe-5">' + token + b"</td>",
                       b'<td class="pe-5">' + token + b"</td><td>A</td>")
    with pytest.raises(ValueError, match="row shape|status column"):
        _alum("1992-02", override={"table-PALUMUSDM.html": tampered})
    tampered = _mutate(b'<th scope="col">VALUE</th>',
                       b'<th scope="col">VALUE</th><th scope="col">STATUS</th>')
    with pytest.raises(ValueError, match="header"):
        _alum("1992-02", override={"table-PALUMUSDM.html": tampered})


def test_non_month_first_or_malformed_dates_raise():
    tampered = _mutate(b'<th scope="row" class="pe-5">1992-02-01</th>',
                       b'<th scope="row" class="pe-5">1992-02-02</th>')
    with pytest.raises(ValueError, match="month-first"):
        _alum("1992-02", override={"table-PALUMUSDM.html": tampered})
    tampered = _mutate(b'<th scope="row" class="pe-5">1992-02-01</th>',
                       b'<th scope="row" class="pe-5">Feb 1992</th>')
    with pytest.raises(ValueError, match="malformed date"):
        _alum("1992-02", override={"table-PALUMUSDM.html": tampered})


def test_date_range_drift_raises():
    tampered = _mutate(b"<td>1992-01-01 to 2026-09-01</td>",
                       b"<td>1992-01-01 to 2026-08-01</td>")
    with pytest.raises(ValueError, match="Date Range"):
        _alum("2026-09", override={"table-PALUMUSDM.html": tampered})


def test_truncated_page_raises():
    raw = body("table-PALUMUSDM.html")
    cut = raw[:raw.index(b"1994-01-01")]  # mid-observations-table: no closing tag
    assert b"1994-01-01" in raw
    with pytest.raises(ValueError, match="truncated|closing tag"):
        _alum("1992-01", override={"table-PALUMUSDM.html": cut})


def test_nested_table_inside_observations_raises():
    token = table_values("PALUMUSDM")["1992-01-01"].encode()
    tampered = _mutate(b'<td class="pe-5">' + token + b"</td>",
                       b'<td class="pe-5"><table><tr><td>1</td></tr></table>' + token +
                       b"</td>")
    with pytest.raises(ValueError, match="nested"):
        _alum("1992-01", override={"table-PALUMUSDM.html": tampered})


@pytest.mark.parametrize("bad", ["N/A", "", "1 234.5", "1e3", "NaN", "1.2.3"])
def test_unreviewed_value_tokens_raise(bad):
    token = table_values("PALUMUSDM")["1992-01-01"].encode()
    tampered = _mutate(b'<td class="pe-5">' + token + b"</td>",
                       b'<td class="pe-5">' + bad.encode() + b"</td>")
    with pytest.raises(ValueError, match="VALUE|unreviewed"):
        _alum("1992-01", override={"table-PALUMUSDM.html": tampered})


# ----------------------------------------------------------------------- evidence envelope

def _decode(evidence: bytes) -> dict:
    doc = json.loads(evidence)
    assert doc["schema"] == "fred-table-evidence" and doc["version"] == 1
    rec = doc["table"]
    return {"url": rec["url"], "status": rec["status"],
            "body": base64.b64decode(rec["body_b64"], validate=True)}


def test_evidence_envelope_is_the_exact_page_record_and_replays_offline():
    r = _alum("2000-06")
    e = entry("table-PALUMUSDM.html")
    assert _decode(r.evidence) == {"url": e["url"], "status": 200,
                                   "body": body("table-PALUMUSDM.html")}
    assert r.evidence_url == e["url"]
    # offline replay (NO http): metadata and values recover from the envelope bytes alone
    unit, values = read_table_page(_decode(r.evidence)["body"], "PALUMUSDM",
                                   registry_specs()[_ALUM])
    assert unit == r.observed_unit and values["2000-06"] == r.observed_text


# ----------------------------------------------------------------------- registration

def test_verifier_registers_and_passes_allowlist():
    v = FredVerifier()
    register_verifier(v)  # the static independence allowlist runs here
    assert get_verifier("fred") is v


def test_verifier_registers_even_in_same_process_as_the_source():
    import ingest.sources.fred  # noqa: F401  (loaded: the static allowlist must still pass)
    register_verifier(FredVerifier())


def test_subprocess_independence():
    assert_verifier_independent("ingest.verifiers.fred",
                                "tests.ingest.fred_verifier_entry:run",
                                source_name="fred",
                                blocked_prefixes=("collectors", "ingest.flags",
                                                  "ingest.sources"))


# ----------------------------------------------------------------------- through the pipeline

@pytest.fixture
def env(db, tmp_path):
    specs = active_specs()
    sync_registry(db, specs)
    return db, specs, RawStore(tmp_path / "raw"), Clock()


def _source():
    return FredSource(api_key=SENTINEL_KEY)


def test_clean_full_run_all_12_verifies_and_stays_unserved(env):
    db, specs, store, clock = env
    r = run_dataset(db, store, _source(), specs, FixtureHttp(), clock)
    assert r.state == "pending-verification"
    assert r.n_written == 12 * 417 and r.n_quarantined == 12 * 144
    assert verify_run(db, r.run_id, FredVerifier(), TableFixtureHttp(), seed=7, specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "verified"
    [(n, passed)] = q(db, "SELECT sample_size, passed FROM verification WHERE "
                          "dataset_run_id=?", r.run_id)
    # one page per series carries its full history: every observation is compared (Task 21)
    assert passed == 1 and n == r.n_written
    # the licence gate: redistribution_ok=false -> even a verified run serves nothing
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]
    # missing '.' cells: non_numeric quarantine only, kept (never dropped, never invented)
    assert q(db, "SELECT reason, COUNT(*) FROM quarantine GROUP BY reason") == \
        [("non_numeric", 1728)]
    # compared surfaces: unit from the HTML metadata, no flag anywhere, evidence archived
    assert q(db, "SELECT COUNT(*) FROM verification_item WHERE observed_unit IS NULL OR "
                 "evidence_sha256 IS NULL OR observed_flag IS NOT NULL") == [(0,)]
    urls = {u for (u,) in q(db, "SELECT evidence_url FROM verification_item")}
    assert urls and all(u.startswith("https://fred.stlouisfed.org/data/") for u in urls)


def test_tampered_value_fails_verification_and_serves_nothing(env):
    """The collector's latest aluminum token is tampered ON THE API BYTES; the independent
    table page still answers the publisher's token — a genuine failed verification."""
    db, specs, store, clock = env
    raw = body("obs-PALUMUSDM.json")
    assert raw.count(b'"value":"3283.054285714286"') == 1
    tampered = raw.replace(b'"value":"3283.054285714286"', b'"value":"3283.054285714287"', 1)
    r = run_dataset(db, store, _source(), specs,
                    FixtureHttp(override={"obs-PALUMUSDM.json": tampered}), clock)
    assert r.state == "pending-verification"
    assert not verify_run(db, r.run_id, FredVerifier(), TableFixtureHttp(), seed=7, specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "failed-verification"
    bad = q(db, "SELECT series_id, period, expected_text, observed_text, note FROM "
                "verification_item WHERE match=0")
    table_token = table_values("PALUMUSDM")["2026-09-01"]
    assert bad == [(_ALUM, "2026-09", "3283.054285714287", table_token, "value differs")]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]


class _BothChannels:
    """run_with_refetch shares one Http between collector and verifier: dispatch by host —
    api.stlouisfed.org carries the api_key (FixtureHttp enforces it), the table page is
    keyless (no api_key on the verifier channel ever)."""

    def __init__(self, collector: FixtureHttp | None = None):
        self.collector = collector or FixtureHttp()
        self.verifier = TableFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if urlsplit(url).netloc == "fred.stlouisfed.org":
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        return self.collector.get(url, params=params, headers=headers, timeout=timeout)


def test_run_with_refetch_registered_verifier_all_12(env):
    db, specs, store, clock = env
    v = FredVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, _source(), v, specs, _BothChannels(), now=clock, max_attempts=1)
    assert res.state == "verified"
    assert q(db, "SELECT passed FROM verification") == [(1,)]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]  # licence gate
    # provenance: every observation comes from the collector's keyed API responses
    urls = {row[0] for row in q(db, "SELECT DISTINCT r.url FROM observation o JOIN raw_fetch "
                                    "r ON r.id = o.raw_fetch_id WHERE o.dataset_run_id = ?",
                                res.run_id)}
    assert urls and all(u.startswith("https://api.stlouisfed.org/fred/series/observations?")
                        and "api_key" not in u for u in urls)


def test_archived_verifier_evidence_replays_offline(env):
    """Every sampled item's evidence_sha256 reloads from the raw store (integrity-checked, no
    HTTP) and decodes to the exact page bytes; value AND unit re-derive from the body alone."""
    db, specs, store, clock = env
    r = run_dataset(db, store, _source(), specs, FixtureHttp(), clock)
    assert verify_run(db, r.run_id, FredVerifier(), TableFixtureHttp(), seed=7, specs=specs, store=store, now=clock)
    rows = q(db, "SELECT series_id, period, evidence_url, evidence_sha256, observed_unit, "
                 "observed_text FROM verification_item")
    assert len(rows) == r.n_written
    by_id = {s.id: s for s in specs}
    rows = rows[::97]  # a spread of items (each decode reparses a whole page)
    for (item_id,) in q(db, "SELECT id FROM verification_item")[::97]:
        assert replay_item(db, store, item_id, FredVerifier())  # reread from evidence alone
    for sid, period, url, sha, unit, token in rows:
        blob = store.load(store.root / "verify-fred" / sha[:2] / sha)  # raises if altered
        rec = _decode(blob)
        assert rec["url"] == url and rec["status"] == 200
        assert rec["body"] == body(f"table-{by_id[sid].native_code}.html")
        got_unit, values = read_table_page(rec["body"], by_id[sid].native_code, by_id[sid])
        assert got_unit == unit and values.get(period) == token


def test_every_item_replays_from_its_archived_evidence_via_reread(env):
    """Task 21 B-I4: replay re-reads the stored evidence with the verifier's pure reread
    (recorded fixtures, no HTTP) and rejects a stored claim the evidence does not support."""
    db, specs, store, clock = env
    r = run_dataset(db, store, _source(), specs, FixtureHttp(), clock)
    assert verify_run(db, r.run_id, FredVerifier(), TableFixtureHttp(), seed=3, specs=specs,
                      store=store, now=clock)
    assert assert_replays_from_evidence(db, store, FredVerifier(), step=211)
