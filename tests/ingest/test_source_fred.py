"""FRED API source adapter tests — real recorded fixtures (tests/ingest/fixtures/fred/,
2026-11-12, sha256-pinned by MANIFEST.json; byte copies of the Task-14 preflight originals with
api_key redacted from every recorded url/params). Pinned (series, period) tokens are
hand-checked against the independent server-rendered data-table HTML (tests-only extraction in
tests/ingest/fred_fixtures.py; the publisher pads table cells with trailing zeros, so
comparisons are exact Decimal, never float).
"""
import json
from urllib.parse import urlsplit

import pytest

from ingest.db import open_db
from ingest.http import HttpResult
from ingest.legacy_import import import_legacy
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources import RawResponse
from ingest.sources.fred import API_BASE, OBS_LIMIT, FredSource, parse_native_code
from ingest.validate import validate
from tests.ingest import legacy_csv
from tests.ingest.fred_fixtures import (
    SENTINEL_KEY,
    FixtureHttp,
    active_specs,
    body,
    entry,
    registry_specs,
    table_values,
)

_OBS_URL = f"{API_BASE}/series/observations"
_META_URL = f"{API_BASE}/series"

# (series id, period) -> publisher token from the archived obs bytes; EVERY pin is Decimal-equal
# to the same DATE/VALUE cell of the recorded data-table HTML (asserted in the pin test).
PINS = {
    ("fred.aluminum.WORLD", "1992-01"): "1181.22729492188",
    ("fred.aluminum.WORLD", "2026-09"): "3283.054285714286",
    ("fred.brent_oil.WORLD", "1992-01"): "18.15652173913043",
    ("fred.brent_oil.WORLD", "2026-09"): "102.0180952380952",
    ("fred.coffee.WORLD", "1992-01"): "73.03181818181818",
    ("fred.coffee.WORLD", "2026-09"): "330.1219047619048",
    ("fred.cotton.WORLD", "1992-01"): "59.6199989318848",
    ("fred.commodity_soybean.WORLD", "2026-09"): "481.7223363582059",
    ("fred.commodity_zinc.WORLD", "2026-09"): "4020.549047619048",
}

# Missing cells: every series' first 144 cells (1980-01 .. 1991-12) are the FRED missing marker
# '.' (archived bytes). The metadata's non-missing range starts 1992-01-01; nothing is truncated.
MISSING_MONTHS = [f"{y}-{m:02d}" for y in range(1980, 1992) for m in range(1, 13)]


def _source() -> FredSource:
    return FredSource(api_key=SENTINEL_KEY)


def _meta(code: str = "PALUMUSDM", **kw) -> RawResponse:
    return RawResponse(url=entry(f"meta-{code}.json")["url"], status=200,
                       params={"series_id": code, "file_type": "json"},
                       body=kw.pop("body_", body(f"meta-{code}.json")))


def _obs(code: str = "PALUMUSDM", **kw) -> RawResponse:
    return RawResponse(url=entry(f"obs-{code}.json")["url"], status=200,
                       params={"series_id": code, "file_type": "json", "limit": str(OBS_LIMIT)},
                       body=kw.pop("body_", body(f"obs-{code}.json")))


def _responses(codes: list[str]) -> list[RawResponse]:
    out = []
    for c in codes:
        out.extend([_meta(c), _obs(c)])
    return out


# ---------------------------------------------------------------- construction / credentials

def test_explicit_api_key_and_env_fallback(monkeypatch):
    assert FredSource(api_key=SENTINEL_KEY).name == "fred"
    monkeypatch.setenv("FRED_API_KEY", SENTINEL_KEY)
    assert FredSource().name == "fred"


def test_missing_api_key_fails_clearly_without_reading_any_file(monkeypatch, tmp_path):
    """No env var and no explicit key must fail mentioning FRED_API_KEY. The production module
    must never read the legacy .fred_api_key file (it exists in the repo root): run the
    constructor in an EMPTY working dir too, so a stray file cannot save it."""
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="FRED_API_KEY"):
        FredSource()


@pytest.mark.parametrize("key", ["", "   "])
def test_blank_api_key_rejected(key):
    with pytest.raises(ValueError, match="api_key"):
        FredSource(api_key=key)


def test_parse_native_code_format():
    assert parse_native_code("PALUMUSDM") == "PALUMUSDM"
    for bad in (None, "", "palumusdm", "PALU MUSDM", "PALUMUSDM:PRT", "P.ALUM", "MÉDIO"):
        with pytest.raises(ValueError):
            parse_native_code(bad)


# --------------------------------------------------------------------- fetch (wire behavior)

def test_fetch_requests_each_active_series_metadata_then_observations():
    specs = active_specs()
    http = FixtureHttp()
    out = list(_source().fetch(specs, http))
    codes = sorted({parse_native_code(s.native_code) for s in specs})
    assert len(codes) == 12
    expected = [(k, c) for c in codes for k in ("meta", "obs")]
    assert http.calls == expected
    assert len(out) == 24
    assert all(r.status == 200 for r in out)


def test_fetch_wire_carries_key_but_archived_identity_is_key_free():
    """The outgoing wire request must carry api_key (FRED query auth); the YIELDED RawResponse
    (the archived identity that lands in the raw store, DB and events) must not: url without an
    api_key param, params dict with api_key explicitly OMITTED (documented in MANIFEST)."""
    out = list(_source().fetch(active_specs(), FixtureHttp()))
    assert SENTINEL_KEY not in repr(out)  # urls, params and bodies are all key-free
    first = out[0]
    assert first.url == entry("meta-PALUMUSDM.json")["url"]
    assert "api_key" not in first.url and "api_key" not in first.params
    assert first.params == {"series_id": "PALUMUSDM", "file_type": "json"}
    obs = out[1]
    assert obs.url == entry("obs-PALUMUSDM.json")["url"]
    assert obs.params == {"series_id": "PALUMUSDM", "file_type": "json", "limit": str(OBS_LIMIT)}


def test_fetch_rejects_a_response_that_echoes_the_credential_before_yielding():
    """A body containing the credential is refused BEFORE yield - the raw bytes are never
    archived, never mutated; the error message must not contain the key."""
    poisoned = body("obs-PALUMUSDM.json") + SENTINEL_KEY.encode()
    http = FixtureHttp(override={"obs-PALUMUSDM.json": poisoned})
    with pytest.raises(ValueError) as ei:
        list(_source().fetch(active_specs()[:1], http))
    assert SENTINEL_KEY not in str(ei.value)


def test_fetch_sanitizes_network_errors_no_url_no_key():
    """An http.get failure (whose exception typically embeds the full request URL INCLUDING the
    query key) is re-raised sanitized: exception type only, series id, endpoint family."""

    class Boom(FixtureHttp):
        def get(self, url, params=None, headers=None, timeout=None):
            q = "&".join(f"{k}={v}" for k, v in (params or {}).items())
            raise ConnectionError(f"boom at {url}?{q}")

    with pytest.raises(ValueError) as ei:
        list(_source().fetch(active_specs()[:1], Boom()))
    assert SENTINEL_KEY not in str(ei.value)
    assert "api_key" not in str(ei.value) and "http" not in str(ei.value)


def test_fetch_yields_incrementally_so_partial_evidence_survives_later_failure():
    class Mid(FixtureHttp):
        def get(self, url, params=None, headers=None, timeout=None):
            r = super().get(url, params=params, headers=headers, timeout=timeout)
            if self.calls[-1] == ("obs", "PALUMUSDM"):
                raise ConnectionError("simulated mid-fetch network death")
            return r

    from ingest.sources.fred import FredRequestError
    it = _source().fetch(active_specs(), Mid())
    got = next(it)  # the metadata response is delivered BEFORE the failure
    assert got.url == entry("meta-PALUMUSDM.json")["url"]
    with pytest.raises(FredRequestError):
        next(it)


# ----------------------------------------------------------------------- parse: happy path

def test_parse_all_12_active_series_offline_full_history():
    specs = active_specs()
    parsed = _source().parse(specs, _responses(sorted({parse_native_code(s.native_code) for s in specs})))
    assert set(parsed) == {s.id for s in specs}
    for s in specs:
        rows = parsed[s.id]
        assert len(rows) == 561  # 417 values + 144 '.' missing cells (1980-01..1991-12)
        assert sum(r.value_raw is None for r in rows) == 144
        assert all(type(r.value_raw) in (str, type(None)) for r in rows)
        assert [r.period_raw for r in rows][:3] == ["1980-01", "1980-02", "1980-03"]
        assert rows[-1].period_raw == "2026-09"
        assert all(r.flag_raw == "normal" for r in rows)
        assert all(r.unit_raw == s.unit for r in rows)  # metadata's actual publisher label
        # rows come from this series' OBSERVATIONS response (fetch order: meta, obs, meta, ...)
        idx = sorted({parse_native_code(s.native_code) for s in specs}).index(s.native_code) * 2 + 1
        assert all(r.response_index == idx for r in rows)


def test_pinned_tokens_match_the_independent_html_table_exactly():
    from decimal import Decimal
    specs = active_specs()
    parsed = _source().parse(specs, _responses(sorted({parse_native_code(s.native_code) for s in specs})))
    by = {(sid, r.period_raw): r.value_raw for sid, rows in parsed.items() for r in rows}
    assert len(PINS) >= 5  # hand-checked against the original HTML (see module docstring)
    code_of = {s.id: parse_native_code(s.native_code) for s in specs}
    for (sid, period), token in PINS.items():
        assert by[(sid, period)] == token  # the API's verbatim string token
        cell = table_values(code_of[sid])[f"{period}-01"]
        assert Decimal(cell) == Decimal(token)  # exact, incl. the table's trailing-zero padding


def test_every_api_value_matches_the_html_table_exactly():
    """Full cross-channel equality as exact Decimal (not only the pins): the controller proved
    417 == 417 per series at intake; this test re-derives it offline from the archived bytes."""
    from decimal import Decimal
    parsed = _source().parse(active_specs(), _responses(
        sorted({parse_native_code(s.native_code) for s in active_specs()})))
    for s in active_specs():
        table = table_values(parse_native_code(s.native_code))
        vals = {r.period_raw: r.value_raw for r in parsed[s.id] if r.value_raw is not None}
        assert len(vals) == 417 and len(table) == 417
        assert all(Decimal(table[f"{p}-01"]) == Decimal(v) for p, v in vals.items())


def test_missing_cells_become_non_numeric_quarantine_not_truncated_history():
    spec = registry_specs()["fred.aluminum.WORLD"]
    parsed = _source().parse([spec], _responses(["PALUMUSDM"]))
    obs, rej = validate(spec, parsed[spec.id])
    assert len(obs) == 417
    assert {r.reason for r in rej} == {"non_numeric"} and len(rej) == 144
    assert sorted(r.period_raw or "" for r in rej) == MISSING_MONTHS  # kept, never dropped
    assert obs[0].period == "1992-01" and obs[-1].period == "2026-09"


def test_tokens_are_publisher_strings_never_floats():
    spec = registry_specs()["fred.aluminum.WORLD"]
    parsed = _source().parse([spec], _responses(["PALUMUSDM"]))
    rows = [r for r in parsed[spec.id] if r.value_raw is not None]
    assert all(type(r.value_raw) is str for r in rows)
    assert parsed[spec.id][-1].value_raw == "3283.054285714286"  # 15 decimals kept verbatim


# -------------------------------------------------------------------- parse: fail-closed

def _mut_obs(code: str, mutate) -> bytes:
    """Synthetic mutation of a genuine archived body, built IN-TEST for shape guards (never
    stored as genuine evidence)."""
    doc = json.loads(body(f"obs-{code}.json"))
    mutate(doc)
    return json.dumps(doc).encode()


def test_parse_rejects_html_error_page():
    html = b"<!DOCTYPE html><html><body>Bad api_key</body></html>"
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="(?i)html|markup"):
        _source().parse([spec], [_meta(), RawResponse(
            url=entry("obs-PALUMUSDM.json")["url"], status=200,
            params={"series_id": "PALUMUSDM", "file_type": "json", "limit": str(OBS_LIMIT)},
            body=html)])


def test_parse_rejects_non_2xx():
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="HTTP 400"):
        _source().parse([spec], [_meta(), RawResponse(
            url=entry("obs-PALUMUSDM.json")["url"], status=400,
            params={"series_id": "PALUMUSDM", "file_type": "json", "limit": str(OBS_LIMIT)},
            body=b'{"error_code":400,"error_message":"Bad request"}')])


def test_parse_rejects_bad_json_and_duplicate_keys():
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="JSON"):
        _source().parse([spec], [_meta(), _obs(body_=b'{"broken":')])
    with pytest.raises(ValueError, match="duplicate"):
        _source().parse([spec], [_meta(), _obs(
            body_=b'{"count":1,"count":1,"observations":[],"limit":100000,"offset":0}')])


def test_parse_rejects_api_error_shape_on_200():
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="error"):
        _source().parse([spec], [_meta(body_=b'{"error_code": 400, "error_message": "x"}'),
                                 _obs()])


def test_parse_rejects_unknown_top_level_or_row_shape():
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="drifted|unexpected"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d.update(suprise_field=1)))])


def test_parse_rejects_unknown_per_observation_status_field():
    """No per-observation status surface exists in FRED; a new one is unreviewed vocabulary."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="status|drift|unreviewed"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d["observations"][0].update(status="A")))])


def test_parse_rejects_non_string_value_primitive():
    """FRED values are JSON STRINGS. A JSON number is an unknown primitive here (opposite of
    REN/WorldBank): never silently coerce."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="string"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d["observations"][-1].update(value=3283.05)))])


def test_parse_rejects_non_month_first_or_bad_dates():
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="month-first|date"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d["observations"][-1].update(date="2026-09-02")))])
    with pytest.raises(ValueError, match="month-first|date"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d["observations"][-1].update(date="2026/09/01")))])


def test_parse_rejects_duplicate_dates_and_realtime_identity_drift():
    spec = registry_specs()["fred.aluminum.WORLD"]
    def dup_last(d):
        d["observations"].append(dict(d["observations"][-1]))
        d["count"] = len(d["observations"])
    with pytest.raises(ValueError, match="duplicate"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs("PALUMUSDM", dup_last))])
    with pytest.raises(ValueError, match="realtime"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d["observations"][0].update(realtime_start="1999-01-01")))])


def test_parse_rejects_truncation_and_count_drift():
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="count"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d.update(count=560)))])
    with pytest.raises(ValueError, match="offset"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d.update(offset=1)))])


def test_parse_rejects_metadata_identity_or_dimension_drift():
    spec = registry_specs()["fred.aluminum.WORLD"]
    meta = json.loads(body("meta-PALUMUSDM.json"))
    for field, value in (("id", "PCOPPUSDM"), ("frequency_short", "Q"),
                         ("seasonal_adjustment_short", "SA"),
                         ("units", "U.S. Dollars per Pound")):
        tampered = json.loads(body("meta-PALUMUSDM.json"))
        tampered["seriess"][0][field] = value
        with pytest.raises(ValueError):
            _source().parse([spec], [_meta(body_=json.dumps(tampered).encode()), _obs()])
    assert meta["seriess"][0]["units"] == "U.S. Dollars per Metric Ton"  # sanity: real bytes


def test_parse_rejects_response_identity_mismatch_or_unrequested_series():
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="unrequested"):
        _source().parse([spec], [_meta("PCOPPUSDM"), _obs("PCOPPUSDM")])
    with pytest.raises(ValueError, match="unrequested"):
        _source().parse([spec], [_meta(), _obs("PCOPPUSDM")])


def test_parse_rejects_archived_params_carrying_the_credential():
    spec = registry_specs()["fred.aluminum.WORLD"]
    leaked = RawResponse(url=entry("obs-PALUMUSDM.json")["url"], status=200,
                         params={"series_id": "PALUMUSDM", "file_type": "json",
                                 "limit": str(OBS_LIMIT), "api_key": "whatever"},
                         body=body("obs-PALUMUSDM.json"))
    with pytest.raises(ValueError, match="api_key"):
        _source().parse([spec], [_meta(), leaked])


def test_parse_needs_metadata_before_rows():
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="metadata"):
        _source().parse([spec], [_obs()])


# ----------------------------------------------------------------- pagination (synthetic)

def _paged(code: str, per: int, pages: int) -> list[RawResponse]:
    """A genuine archived single-page body RE-PAGED in-test into synthetic multi-page responses
    (mutation built only for the pagination guard tests; never stored as genuine evidence)."""
    doc = json.loads(body(f"obs-{code}.json"))
    obs = doc["observations"]
    out = []
    for p in range(pages):
        chunk = dict(doc, observations=obs[p * per:(p + 1) * per])
        chunk["limit"] = per
        chunk["offset"] = p * per
        params = {"series_id": code, "file_type": "json", "limit": str(per)}
        if p:
            params["offset"] = str(p * per)
        url = entry(f"obs-{code}.json")["url"].split("?")[0] + "?" + \
            "&".join(f"{k}={v}" for k, v in params.items())
        out.append(RawResponse(url=url, params=params, status=200,
                               body=json.dumps(chunk).encode()))
    return out


def test_pagination_concatenates_pages_with_response_index_provenance():
    spec = registry_specs()["fred.aluminum.WORLD"]
    pages = _paged("PALUMUSDM", 300, 2)  # 300 + 261 of 561
    parsed = _source().parse([spec], [_meta(), *pages])
    assert len(parsed[spec.id]) == 561
    assert [r.response_index for r in parsed[spec.id]][:300] == [1] * 300
    assert [r.response_index for r in parsed[spec.id]][300:] == [2] * 261
    full = _source().parse([spec], _responses(["PALUMUSDM"]))[spec.id]
    assert [(r.period_raw, r.value_raw) for r in parsed[spec.id]] == \
        [(r.period_raw, r.value_raw) for r in full]


def test_pagination_offset_drift_or_duplicate_page_raises():
    spec = registry_specs()["fred.aluminum.WORLD"]
    pages = _paged("PALUMUSDM", 300, 2)
    with pytest.raises(ValueError, match="offset|contiguous"):
        _source().parse([spec], [_meta(), pages[1], pages[0]])
    with pytest.raises(ValueError, match="offset|duplicate"):
        _source().parse([spec], [_meta(), pages[0], pages[0]])


# --------------------------------------------------------------- pipeline + secret hygiene

def test_pipeline_full_registry_offline_quarantines_and_licence_gate(tmp_path):
    """End to end on recorded bytes: 12 series x 417 rows written (unit metadata from the live
    metadata response), 12 x 144 '.' cells quarantined non_numeric; even in state 'verified',
    redistribution_ok=false keeps served = 0."""
    specs = active_specs()
    db = open_db(tmp_path / "t.db")
    try:
        sync_registry(db, specs)
        r = run_dataset(db, RawStore(tmp_path / "raw"), _source(), specs, FixtureHttp())
        assert r.state == "pending-verification"
        assert r.n_written == 12 * 417 and r.n_quarantined == 12 * 144
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0] == 0
        db.set_run_state(r.run_id, "verified", finished_at="2026-11-12T00:00:00+00:00")
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0] == 0
        # every observation's raw_fetch is an /series/observations response (never the metadata)
        urls = {row[0] for row in db.conn.execute(
            "SELECT DISTINCT r.url FROM observation o JOIN raw_fetch r ON r.id = o.raw_fetch_id"
            " WHERE o.dataset_run_id = ?", (r.run_id,))}
        assert urls and all("/series/observations?" in u for u in urls)
        # the 24 archived responses include both endpoints per series
        assert db.conn.execute("SELECT COUNT(*) FROM raw_fetch WHERE dataset_run_id=?",
                               (r.run_id,)).fetchone()[0] == 24
    finally:
        db.close()


def test_pipeline_artifacts_never_contain_the_credential(tmp_path, capsys):
    """Sentinel sweep: persisted raw-store bytes, DB raw_fetch url/params_json and event rows
    must all be free of the sentinel key after success, http error AND parse failure."""
    specs = active_specs()
    for http in (FixtureHttp(),
                 FixtureHttp(status={("meta", "PALUMUSDM"): 500}),
                 FixtureHttp(override={"obs-PALUMUSDM.json": b'{"broken":'})):
        db = open_db(tmp_path / f"t{len(list(tmp_path.iterdir()))}.db")
        try:
            sync_registry(db, specs)
            run_dataset(db, RawStore(tmp_path / "raw"), _source(), specs, http)
            for row in db.conn.execute(
                    "SELECT url, params_json FROM raw_fetch").fetchall():
                assert SENTINEL_KEY not in (row[0] or "") and SENTINEL_KEY not in (row[1] or "")
                assert "api_key" not in (row[0] or "") and "api_key" not in (row[1] or "")
            for (detail,) in db.conn.execute("SELECT detail_json FROM event").fetchall():
                assert SENTINEL_KEY not in (detail or "")
        finally:
            db.close()
    for f in (tmp_path / "raw").rglob("*"):
        if f.is_file():
            assert SENTINEL_KEY.encode() not in f.read_bytes(), f
    assert SENTINEL_KEY not in capsys.readouterr().out


# ------------------------------------------------------- legacy rows are NOT relabelled

def test_legacy_usd_rows_are_rejected_unit_mismatch_not_relabelled(tmp_path):
    """The unit correction applies to FRESH publisher data only. A legacy row filed under the
    old bare 'USD' label must be quarantined unit_mismatch by the EXISTING importer path (no
    importer change); a row carrying the new exact publisher label imports as usual;
    blank-unit rows keep the Ruling-V missing_unit quarantine. Also: the legacy
    commodity_cotton orphan stays not_in_registry."""
    path = legacy_csv.write_csv(tmp_path / "legacy.csv", [
        ("FRED", "aluminum", "GLOBAL", "1992-01", "1181.22729492188", "USD"),
        ("FRED", "aluminum", "GLOBAL", "1992-02", "1270.75000000000", ""),
        ("FRED", "aluminum", "GLOBAL", "2026-09", "3283.054285714286",
         "U.S. Dollars per Metric Ton"),
        ("FRED", "commodity_cotton", "GLOBAL", "2026-09", "0.958404761904762",
         "U.S. Dollars per Metric Ton"),
    ])
    db = open_db(tmp_path / "t.db")
    try:
        rep = import_legacy(db, path)  # default registry: the real registry/core.yaml
        assert rep.n_imported == 1
        assert rep.n_quarantined_by_reason == {"unit_mismatch": 1, "missing_unit": 1,
                                               "not_in_registry": 1}
        rows = db.conn.execute("SELECT period, value_text, series_id FROM observation").fetchall()
        assert rows == [("2026-09", "3283.054285714286", "fred.aluminum.WORLD")]
        reasons = sorted(db.conn.execute(
            "SELECT raw_period, reason FROM quarantine").fetchall())
        assert reasons == [("1992-01", "unit_mismatch"), ("1992-02", "missing_unit")]
    finally:
        db.close()


# ============================== fix round 1 regressions (quality review I1) ==============
# I1: an archived FRED corpus must be COMPLETE and STABLE per series: page offsets contiguous
# from 0, final accumulated rows == the payload-declared count, identical count/limit/
# realtime/extent on every page, strictly ascending dates, every row date within the declared
# observation extent, and a strict url-query/params identity. The genuine archived envelope is
# the broad 1600-01-01..9999-12-31 no-restriction echo, so endpoints are NOT asserted equal
# to first/last rows - containment and count reconciliation are the contract.

def test_parse_rejects_a_truncated_archive_that_keeps_the_declared_count():
    """Review P1: obs payload truncated to 300 rows with count=561 intact must fail closed -
    never ingest a partial history error-free (missing periods produce no verification items,
    so the loss would be invisible downstream)."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    def trunc(d):
        d["observations"] = d["observations"][:300]
    with pytest.raises(ValueError, match="(?i)incomplete|truncat|missing|tail|count"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs("PALUMUSDM", trunc))])


def test_parse_rejects_an_archive_missing_its_tail_page():
    """Same completeness contract over multi-page archives: only page 1 of 2 present => the
    accumulated 300 rows never reach the declared count 561."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    first_page_only = _paged("PALUMUSDM", 300, 2)[:1]
    with pytest.raises(ValueError, match="(?i)incomplete|missing|tail|count"):
        _source().parse([spec], [_meta(), *first_page_only])


def test_parse_rejects_a_series_with_metadata_but_no_observations_page():
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="(?i)observations|incomplete|no .*page"):
        _source().parse([spec], [_meta()])


def test_parse_rejects_rows_outside_the_declared_observation_extent():
    """Review P4: envelope observation_start/end are the publisher's declared request extent.
    Every row date must stay within it (the genuine envelope is broad 1600-01-01..9999-12-31,
    so containment - not endpoint equality - is the assertion)."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="(?i)extent|observation_start|outside"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d.update(observation_start="2010-01-01")))])
    with pytest.raises(ValueError, match="(?i)extent|observation_end|outside"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
            "PALUMUSDM", lambda d: d.update(observation_end="2020-01-01")))])


def test_parse_rejects_count_or_extent_drift_across_pages():
    """Mid-archive instability: page 2 declares a different total count or observation extent
    than page 1. Cross-page identity is pinned from the FIRST page."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    pages = _paged("PALUMUSDM", 300, 2)

    def mutate_page2(mut):
        d = json.loads(pages[1].body)
        mut(d)
        return RawResponse(url=pages[1].url, params=pages[1].params, status=200,
                           body=json.dumps(d).encode())

    grown = mutate_page2(lambda d: d.update(count=600))  # per-page bounds still coherent
    with pytest.raises(ValueError, match="(?i)count.*drift|drift.*count|count"):
        _source().parse([spec], [_meta(), pages[0], grown])
    narrowed = mutate_page2(lambda d: d.update(observation_end="2026-08-31"))
    with pytest.raises(ValueError, match="(?i)extent|observation|drift|outside"):
        _source().parse([spec], [_meta(), pages[0], narrowed])


def test_parse_rejects_unreviewed_duplicate_or_mismatched_url_query_keys():
    """Review P3/M3: the archived URL query must be a strict projection of the reviewed params -
    unreviewed keys (e.g. a restriction the params never declared), duplicated keys, and
    query/param value disagreements all fail closed. params may carry identity by themselves
    (the happy-path fixtures already cover that positive)."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    good = entry("obs-PALUMUSDM.json")["url"]
    base = good.split("?")[0]
    ok_params = {"series_id": "PALUMUSDM", "file_type": "json", "limit": str(OBS_LIMIT)}
    obs = body("obs-PALUMUSDM.json")
    cases = [
        RawResponse(url=good + "&observation_start=2010-01-01", params=dict(ok_params),
                    status=200, body=obs),  # unreviewed restriction key in the URL
        RawResponse(url=base + "?series_id=PALUMUSDM&series_id=PALUMUSDM&file_type=json"
                               "&limit=100000", params=dict(ok_params), status=200, body=obs),
        RawResponse(url=base + "?series_id=PALUMUSDM&file_type=json&limit=99999",
                    params=dict(ok_params), status=200, body=obs),  # value disagreement
        RawResponse(url=good, params={"series_id": "PALUMUSDM", "file_type": "json"},
                    status=200, body=obs),  # URL carries a key the params never declared
    ]
    for resp in cases:
        with pytest.raises(ValueError, match="(?i)query|params|duplicate|drift|disagree"):
            _source().parse([spec], [_meta(), resp])


def test_parse_rejects_non_canonical_or_wrong_archived_param_literals():
    """Archived limit/offset literals must be canonical ASCII decimals and file_type must be the
    literal 'json' - a tampered archive cannot smuggle identity through formatting."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    url = entry("obs-PALUMUSDM.json")["url"]
    obs = body("obs-PALUMUSDM.json")
    for params in ({"series_id": "PALUMUSDM", "file_type": "json", "limit": "0100000"},
                   {"series_id": "PALUMUSDM", "file_type": "json", "limit": str(OBS_LIMIT),
                    "offset": "00"},
                   {"series_id": "PALUMUSDM", "file_type": "JSON", "limit": str(OBS_LIMIT)}):
        resp = RawResponse(url=url, params=params, status=200, body=obs)
        with pytest.raises(ValueError, match="(?i)canonical|file_type|limit|offset|disagree"):
            _source().parse([spec], [_meta(), resp])


# ------------------------------------------- multi-page fetch stability (I1, fetch-side)

class _PagedHttp(FixtureHttp):
    """FixtureHttp is single-page only (limit=100000 exceeds every archived series). This double
    serves the genuine archived obs body RE-SLICED by the request's offset/limit so the
    multi-page fetch path is exercised; the drift_* flags simulate a mid-pagination unstable
    publisher (tamper built in-test, never stored as genuine evidence)."""

    def __init__(self, code: str = "PALUMUSDM", drift_realtime: bool = False,
                 drift_extent: bool = False, drift_limit: bool = False):
        super().__init__()
        self.code = code
        self.drift_realtime = drift_realtime
        self.drift_extent = drift_extent
        self.drift_limit = drift_limit

    def get(self, url, params=None, headers=None, timeout=None):
        p = {k: str(v) for k, v in (params or {}).items()}
        assert p.get("api_key"), f"FRED wire request must carry the credential: {params}"
        if urlsplit(url).path != "/fred/series/observations":
            return super().get(url, params=params, headers=headers, timeout=timeout)
        off, lim = int(p.get("offset", "0")), int(p["limit"])
        doc = json.loads(body(f"obs-{self.code}.json"))
        rows = doc["observations"][off:off + lim]
        page = dict(doc, observations=rows, offset=off, limit=lim)
        if off:
            if self.drift_realtime:
                page["realtime_end"] = "1999-12-31"
                for r in rows:  # keep the page internally consistent: only CROSS-page drift
                    r["realtime_end"] = "1999-12-31"
            if self.drift_extent:
                page["observation_end"] = "2026-08-31"  # excludes the genuine 2026-09-01 tail
            if self.drift_limit:
                page["limit"] = lim + 1
        q = "&".join(f"{k}={v}" for k, v in p.items() if k != "api_key")
        self.calls.append(("obs", self.code))
        return HttpResult(status=200, body=json.dumps(page).encode(), url=f"{url}?{q}")


def test_fetch_paginates_to_a_complete_stable_archive(monkeypatch):
    """Happy path over the multi-page fetch loop (OBS_LIMIT patched small): two coherent pages
    concatenate to exactly the single-page archive, with per-page response_index provenance."""
    monkeypatch.setattr("ingest.sources.fred.OBS_LIMIT", 300)
    spec = registry_specs()["fred.aluminum.WORLD"]
    http = _PagedHttp()
    out = list(_source().fetch([spec], http))
    assert http.calls == [("meta", "PALUMUSDM"), ("obs", "PALUMUSDM"), ("obs", "PALUMUSDM")]
    assert len(out) == 3 and all(r.status == 200 for r in out)
    assert SENTINEL_KEY not in repr(out)  # archived identity stays key-free over pagination
    parsed = _source().parse([spec], out)
    full = _source().parse([spec], _responses(["PALUMUSDM"]))[spec.id]
    assert [(r.period_raw, r.value_raw) for r in parsed[spec.id]] == \
        [(r.period_raw, r.value_raw) for r in full]
    assert [r.response_index for r in parsed[spec.id]][:300] == [1] * 300
    assert [r.response_index for r in parsed[spec.id]][300:] == [2] * 261


@pytest.mark.parametrize("flag", ["drift_realtime", "drift_extent", "drift_limit"])
def test_fetch_rejects_cross_page_identity_drift_mid_pagination(monkeypatch, flag):
    """The run must fail closed AT the drifting page (never promote a short/unstable archive):
    realtime, observation extent and page limit are pinned from the first page."""
    monkeypatch.setattr("ingest.sources.fred.OBS_LIMIT", 300)
    spec = registry_specs()["fred.aluminum.WORLD"]
    with pytest.raises(ValueError, match="(?i)realtime|extent|limit|drift|outside"):
        list(_source().fetch([spec], _PagedHttp(**{flag: True})))


# ============================== fix round 1 regressions (quality review I2) ==============
# I2: dates are canonical ASCII YYYY-MM-DD Gregorian. \d is Unicode-aware; unicode aliases
# bypassed the duplicate check as distinct period keys before normalize_period collapsed them.

ARABIC_INDIC_MONTH_01 = "2026-٠١-01"  # ٠١ = '01' in Arabic-Indic digits, aliases 2026-01


def test_parse_rejects_unicode_digit_date_aliases():
    """Review P2: a row carrying Arabic-Indic digits reached validate() as a distinct period
    key alongside the genuine 2026-09. The source trust boundary must reject non-ASCII dates;
    the pipeline-level refusal is pinned separately below."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    def alias(d):
        row = dict(d["observations"][-1])
        row["date"] = ARABIC_INDIC_MONTH_01
        d["observations"].append(row)
        d["count"] += 1
    with pytest.raises(ValueError, match="(?i)ascii|date"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs("PALUMUSDM", alias))])
    def alias_inplace(d):  # aliasing a genuine row, not only an appended one
        d["observations"][0]["date"] = "١٩٨٠-٠١-٠١"
    with pytest.raises(ValueError, match="(?i)ascii|date"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs("PALUMUSDM", alias_inplace))])


def test_parse_rejects_dates_that_are_ascii_but_not_gregorian():
    """ASCII digits are necessary not sufficient: the date must exist on the Gregorian calendar.
    Row dates already pass the month-first (day==01) gate, so year-0000 is the reachable
    row-level hole; envelope/realtime fields carry genuine day-of-month values (9999-12-31),
    where a Feb 30 sailed through pre-fix. Values stay verbatim: no normalization/repair."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    def year0_row(d):  # distinct extra row: the date check fires, never a duplicate collision
        row = dict(d["observations"][-1])
        row["date"] = "0000-01-01"
        d["observations"].append(row)
        d["count"] += 1
    with pytest.raises(ValueError, match="(?i)gregorian|date"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs("PALUMUSDM", year0_row))])
    for bad in ("9999-02-30", "0000-01-01"):  # month_first=False envelope fields
        with pytest.raises(ValueError, match="(?i)gregorian|date"):
            _source().parse([spec], [_meta(), _obs(body_=_mut_obs(
                "PALUMUSDM", lambda d, b=bad: d.update(observation_end=b)))])


def test_parse_rejects_unicode_digit_realtime_and_last_updated():
    """Realtime bounds and last_updated keep the same canonical-ASCII rule (metadata dates were
    already _date-validated; the obs envelope realtime and last_updated shape were not)."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    def rt_alias(d):
        for r in d["observations"]:  # keep the page internally consistent
            r["realtime_end"] = "2026-١٠-23"
        d["realtime_end"] = "2026-١٠-23"
    with pytest.raises(ValueError, match="(?i)ascii|date|realtime"):
        _source().parse([spec], [_meta(), _obs(body_=_mut_obs("PALUMUSDM", rt_alias))])
    meta = json.loads(body("meta-PALUMUSDM.json"))
    meta["seriess"][0]["last_updated"] = "2026-١٠-22 14:26:54-05"
    with pytest.raises(ValueError, match="(?i)last_updated|drift|date|ascii"):
        _source().parse([spec], [_meta(body_=json.dumps(meta).encode()), _obs()])


# -------------------------------------- full-pipeline refusal of tampered archives (I1+I2)

def test_pipeline_refuses_a_truncated_or_unicode_aliased_archive_and_writes_nothing(tmp_path):
    """End-to-end on recorded bytes with only the PALUMUSDM obs body tampered in-test: the run
    must end failed (no promotion), with zero observations and the byte evidence kept - never
    a silently shortened history or a unicode-aliased period reaching the DB/verifier."""
    specs = active_specs()

    def truncated(d):
        d["observations"] = d["observations"][:300]

    def aliased(d):
        row = dict(d["observations"][-1])
        row["date"] = ARABIC_INDIC_MONTH_01
        d["observations"].append(row)
        d["count"] += 1

    for i, tamper in enumerate((truncated, aliased)):
        poisoned = _mut_obs("PALUMUSDM", tamper)
        db = open_db(tmp_path / f"t{i}.db")
        try:
            sync_registry(db, specs)
            r = run_dataset(db, RawStore(tmp_path / f"raw{i}"), _source(), specs,
                            FixtureHttp(override={"obs-PALUMUSDM.json": poisoned}))
            assert r.state.startswith("failed-") and r.n_written == 0
            assert db.conn.execute("SELECT COUNT(*) FROM observation").fetchone()[0] == 0
            assert db.conn.execute("SELECT COUNT(*) FROM raw_fetch WHERE dataset_run_id=?",
                                   (r.run_id,)).fetchone()[0] > 0  # evidence kept
        finally:
            db.close()


# ============================== fix round 2 regression (quality re-review) ==================
# The params identity is a SUBSET contract - the same one the URL query side already asserts
# (`not set(q) <= allowed`, fred.py _identify). A strict-superset test lets ONE unknown
# archived key ride along whenever a reviewed optional key is absent from the params - i.e.
# `offset` on every first page. Any unreviewed param key must fail closed.

@pytest.mark.parametrize("extra_key,extra_value", [
    ("observation_start", "2010-01-01"),
    ("frequency", "m"),
    ("units", "lin"),
])
def test_parse_rejects_params_with_an_unreviewed_key(extra_key, extra_value):
    """Re-review blocker: `set(params) > allowed` misses a single unknown key on an archived
    first page (no `offset`, so the tampered key set is not a strict superset). URL, body and
    every reviewed param stay genuine, so ONLY the params-subset guard can raise."""
    spec = registry_specs()["fred.aluminum.WORLD"]
    genuine = _obs()
    resp = RawResponse(url=genuine.url, status=genuine.status,
                       params={**(genuine.params or {}), extra_key: extra_value},
                       body=genuine.body)
    with pytest.raises(ValueError, match="(?i)archived params drifted"):
        _source().parse([spec], [_meta(), resp])


def test_parse_rejects_an_unreviewed_restriction_param_on_a_self_consistent_window():
    """The exact smuggle shape: unknown `observation_start` param plus a body whose envelope
    AGREES with it - 201 monthly rows from 2010-01-01, count declared 201 - so truncation,
    count, extent, canonicality and limit/offset guards all stay silent. Only the params
    identity fails closed."""
    spec = registry_specs()["fred.aluminum.WORLD"]

    def window(d):
        d["observations"] = [r for r in d["observations"] if r["date"] >= "2010-01-01"]
        assert len(d["observations"]) == 201  # pin the intended self-consistent window
        d["count"] = len(d["observations"])
        d["observation_start"] = "2010-01-01"  # envelope agrees with the smuggled param

    genuine = _obs(body_=_mut_obs("PALUMUSDM", window))
    resp = RawResponse(url=genuine.url, status=genuine.status,
                       params={**(genuine.params or {}), "observation_start": "2010-01-01"},
                       body=genuine.body)
    with pytest.raises(ValueError, match="(?i)archived params drifted"):
        _source().parse([spec], [_meta(), resp])
