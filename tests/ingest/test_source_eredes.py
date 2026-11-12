"""E-REDES source adapter tests — recorded genuine fixtures (tests/ingest/fixtures/eredes/,
2026-11-12, MANIFEST.json). Synthetic doubles/mutations are labelled synthetic in-line.
"""
import json
from datetime import date

import pytest

from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources import RawResponse
from ingest.sources.eredes import PAGE_SIZE, PRODUCTION_DATASET, EredesSource, parse_native_code
from ingest.validate import validate
from tests.ingest.eredes_fixtures import FixtureHttp, all_specs, body, registry_specs

# Named exact samples from the genuine recorded window (window_json.body, byte-checked against
# the independent exports/csv of the same window at recording time).
EXACT = [  # (period, dgm, pre, total)
    ("2026-11-10T00:00:00+00:00", "925741.0", "535073.0", "1460814.0"),
    ("2026-11-10T00:15:00+00:00", "927869.0", "523992.0", "1451861.0"),
    ("2026-11-10T06:30:00+00:00", "1035020.0", "305265.0", "1340285.0"),
    ("2026-11-10T12:00:00+00:00", "1393848.0", "457367.0", "1851215.0"),
    ("2026-11-10T18:45:00+00:00", "1555728.0", "415834.0", "1971562.0"),
    ("2026-11-10T23:30:00+00:00", "1132027.0", "419192.0", "1551219.0"),
    ("2026-11-10T23:45:00+00:00", "1097652.0", "421768.0", "1519420.0"),
]


def _window_source():
    return EredesSource(from_ts="2026-11-10T00:00:00+00:00", to_ts="2026-11-11T00:00:00+00:00")


def _responses():
    """The RawResponse list the real fetch() would yield for the recorded one-day window."""
    from tests.ingest.eredes_fixtures import MANIFEST

    def rr(name):
        m = MANIFEST["sets"][name]
        return RawResponse(url=m["url"], params=m["params"], status=m["status"],
                           body=body(name))
    return [rr("metadata"), rr("window_json")]


# --- native_code contract ---------------------------------------------------------------------

def test_parse_native_code_ok():
    assert parse_native_code(f"{PRODUCTION_DATASET}:dgm") == (PRODUCTION_DATASET, "dgm")


@pytest.mark.parametrize("code", [
    None, "", "dgm", f"{PRODUCTION_DATASET}:", ":dgm",
    f"{PRODUCTION_DATASET}:total:extra",
    f"{PRODUCTION_DATASET}:TOTAL",                    # case drift
    "consumo-total-nacional:total",                   # unreviewed dataset
    f"{PRODUCTION_DATASET}:datahora",                 # not a value field
])
def test_parse_native_code_rejects_unreviewed(code):
    with pytest.raises(ValueError):
        parse_native_code(code)


# --- window contract --------------------------------------------------------------------------

def test_default_window_is_the_last_complete_utc_days():
    src = EredesSource(today=date(2026, 11, 12))
    assert src.days == (date(2026, 11, 9), date(2026, 11, 10), date(2026, 11, 11))


def test_explicit_window_days():
    src = EredesSource(from_ts="2026-04-01T00:00:00+00:00", to_ts="2026-04-04T00:00:00+00:00")
    assert src.days == (date(2026, 4, 1), date(2026, 4, 2), date(2026, 4, 3))


@pytest.mark.parametrize("frm,to", [
    ("2026-04-01T00:00:00+00:00", None),              # one-sided
    (None, "2026-04-02T00:00:00+00:00"),
    ("2026-04-02T00:00:00+00:00", "2026-04-02T00:00:00+00:00"),  # empty
    ("2026-04-03T00:00:00+00:00", "2026-04-02T00:00:00+00:00"),  # reversed
    ("2026-04-01T01:15:00+00:00", "2026-04-02T00:00:00+00:00"),  # not a day boundary
    ("2026-04-01T00:00:00Z", "2026-04-02T00:00:00+00:00"),       # non-canonical spelling
    ("2026-04-01", "2026-04-02"),                                # dates, not timestamps
])
def test_window_rejects_malformed_bounds(frm, to):
    with pytest.raises(ValueError):
        EredesSource(from_ts=frm, to_ts=to)


# --- fetch: metadata + one page per UTC day, nothing silently capped --------------------------

def test_fetch_requests_metadata_then_the_window_page():
    src = _window_source()
    http = FixtureHttp()
    responses = list(src.fetch(all_specs(), http))
    assert http.calls == ["metadata", "window_json"]
    assert responses[0].params is None and responses[1].params["where"] == \
        'datahora >= "2026-11-10" AND datahora < "2026-11-11"'
    assert responses[1].params["order_by"] == "datahora"
    assert responses[1].params["limit"] == PAGE_SIZE


class _SyntheticPagedHttp:
    """SYNTHETIC labelled double: answers /records pages whose total_count is given, and the
    metadata route with the genuine fixture. A protocol-shape double for the fetch pagination
    contract only - its rows are not parsed (150 quarter-hours cannot fit one real UTC day)."""

    def __init__(self, total=150):
        self.total, self.calls = total, []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(dict(params or {}))
        if url.endswith("/records"):
            offset = int((params or {}).get("offset", 0))
            n = min(PAGE_SIZE, max(self.total - offset, 0))
            rows = [{"datahora": "2026-11-10T00:00:00+00:00", "dia": "10", "mes": "11",
                     "ano": "2026", "date": "2026-11-10", "time": "00:00",
                     "dgm": 1.0, "pre": 2.0, "total": 3.0}] * n
            return HttpResultShim(200, json.dumps(
                {"total_count": self.total, "results": rows}).encode(), url)
        return HttpResultShim(200, body("metadata"), url)


class HttpResultShim:
    """Minimal HttpResult-compatible double for the synthetic paginator."""

    def __init__(self, status, body_, url):
        self.status, self.body, self.url = status, body_, url


def test_fetch_pages_every_page_of_a_dense_synthetic_window():
    http = _SyntheticPagedHttp(total=150)
    responses = list(_window_source().fetch(all_specs(), http))
    pages = [c for c in http.calls if "where" in c]
    assert [c.get("offset", 0) for c in pages] == [0, 100]
    assert len(responses) == 3  # metadata + 2 record pages


def test_fetch_refuses_windows_beyond_the_offset_cap():
    """No silent truncation: a denser-than-possible window must fail, not stop at 100/10000."""
    http = _SyntheticPagedHttp(total=100 * PAGE_SIZE + 1)
    with pytest.raises(ValueError, match="10000|offset|completeness"):
        list(_window_source().fetch(all_specs(), http))


def _split_genuine_window(cut=50):
    """The genuine 96-record window re-paginated into two responses (parse-completeness double:
    genuine tokens, only the page split is synthetic)."""
    responses = _responses()
    doc = json.loads(body("window_json"))
    pages = []
    for offset, chunk in ((0, doc["results"][:cut]), (cut, doc["results"][cut:])):
        synthetic = json.dumps({"total_count": doc["total_count"], "results": chunk}).encode()
        params = {**(responses[1].params or {}), "limit": cut}
        if offset:
            params["offset"] = offset
        pages.append(RawResponse(url=responses[1].url, params=params, status=200,
                                 body=synthetic))
    return pages


def test_parse_concatenates_split_genuine_pages_completely():
    responses = [_responses()[0], *_split_genuine_window()]
    rows = _window_source().parse(all_specs(), responses)
    assert len(rows["eredes.production_total.PT"]) == 96
    got = {(r.period_raw, r.value_raw) for r in rows["eredes.production_total.PT"]}
    want = {(doc["datahora"], doc["total"]) for doc in
            json.loads(body("window_json"), parse_float=str)["results"]}
    assert got == want


def test_parse_rejects_total_count_drift_between_pages():
    pages = _split_genuine_window()
    doc1 = json.loads(pages[1].body, parse_float=str)
    drifted = json.dumps({**doc1, "total_count": 97}).encode()
    with pytest.raises(ValueError, match="total_count"):
        _window_source().parse(all_specs(), [_responses()[0], pages[0],
                                             RawResponse(url=pages[1].url, params=pages[1].params,
                                                         status=200, body=drifted)])


def test_parse_rejects_a_missing_page():
    pages = _split_genuine_window()
    with pytest.raises(ValueError, match="total_count|complete|offset"):
        _window_source().parse(all_specs(), [_responses()[0], pages[0]])


# --- parse: exact native tokens on the genuine fixture ----------------------------------------

def test_parse_genuine_window_exact_tokens():
    rows = _window_source().parse(all_specs(), _responses())
    assert set(rows) == set(registry_specs())
    assert all(len(r) == 96 for r in rows.values())
    by_key = {s.id: {(r.period_raw, r.value_raw) for r in rows[s.id]}
              for s in all_specs()}
    for period, dgm, pre, total in EXACT:
        assert (period, dgm) in by_key["eredes.production_market.PT"]
        assert (period, pre) in by_key["eredes.production_special.PT"]
        assert (period, total) in by_key["eredes.production_total.PT"]
    some = rows["eredes.production_market.PT"][0]
    assert type(some.value_raw) is str and some.value_raw.endswith(".0")  # native float token
    assert some.unit_raw is None and some.flag_raw is None
    assert all(r.response_index == 1 for r in rows["eredes.production_total.PT"])


def test_parse_tokens_validate_to_canonical_observations():
    rows = _window_source().parse(all_specs(), _responses())
    spec = registry_specs()["eredes.production_market.PT"]
    obs, rej = validate(spec, rows[spec.id])
    assert not rej and len(obs) == 96
    o = [o for o in obs if o.period == "2026-11-10T23:45:00+00:00"][0]
    assert o.value_text == "1097652.0" and o.value == 1097652.0 and o.status_flag is None


def test_parse_preserves_negative_dgm_verbatim():
    """E-REDES dgm can legitimately be negative (pumping/storage); never clamped. SYNTHETIC
    single-record payload (built from the genuine shape, labelled synthetic)."""
    doc = json.loads(body("window_json"))
    doc["total_count"] = 1
    doc["results"] = [dict(doc["results"][0], dgm=-50.25)]
    synthetic = json.dumps(doc).encode()
    responses = [_responses()[0], RawResponse(url=_responses()[1].url,
                                              params=_responses()[1].params, status=200,
                                              body=synthetic)]
    rows = _window_source().parse(all_specs(), responses)
    (row,) = rows["eredes.production_market.PT"]
    assert row.value_raw == "-50.25"
    obs, rej = validate(registry_specs()["eredes.production_market.PT"],
                        rows["eredes.production_market.PT"])
    assert not rej and obs[0].value == -50.25


# --- parse fail-closed on drift (synthetic mutations of genuine bytes) -------------------------

def _mutate_window(old: bytes, new: bytes) -> list[RawResponse]:
    return [_responses()[0], RawResponse(url=_responses()[1].url, params=_responses()[1].params,
                                         status=200,
                                         body=body("window_json").replace(old, new, 1))]


def test_parse_rejects_quoted_number():
    with pytest.raises(ValueError, match="number token"):
        _window_source().parse(all_specs(), _mutate_window(b'"dgm": 925741.0',
                                                           b'"dgm": "925741.0"'))


def test_parse_rejects_duplicate_json_key():
    with pytest.raises(ValueError, match="duplicate"):
        _window_source().parse(all_specs(), _mutate_window(b'"total": 1460814.0}',
                                                           b'"total": 1460814.0, "total": 1.0}'))


def test_parse_rejects_noncanonical_timestamp():
    with pytest.raises(ValueError, match="datahora"):
        _window_source().parse(all_specs(), _mutate_window(b"2026-11-10T00:15:00+00:00",
                                                           b"2026-11-10 00:15:00+00:00"))


def test_parse_rejects_duplicate_timestamp():
    # mutate record 2's datahora AND its time echo consistently so the duplicate itself fires
    old = (b'"datahora": "2026-11-10T00:15:00+00:00", "dia": "10", "mes": "11", '
           b'"ano": "2026", "date": "2026-11-10", "time": "00:15"')
    new = (b'"datahora": "2026-11-10T00:00:00+00:00", "dia": "10", "mes": "11", '
           b'"ano": "2026", "date": "2026-11-10", "time": "00:00"')
    with pytest.raises(ValueError, match="ascending|duplicate"):
        _window_source().parse(all_specs(), _mutate_window(old, new))


def test_parse_rejects_unknown_record_key():
    with pytest.raises(ValueError, match="key"):
        _window_source().parse(all_specs(), _mutate_window(b'"dgm": 925741.0',
                                                           b'"dgm": 925741.0, "quality": "Q"'))


def test_parse_rejects_date_column_inconsistent_with_datahora():
    with pytest.raises(ValueError, match="date|dia|mes|ano|time"):
        _window_source().parse(all_specs(), _mutate_window(b'"date": "2026-11-10"',
                                                           b'"date": "2026-11-11"'))


def test_parse_rejects_incomplete_window():
    """total_count 96 but only 95 results = a missing record: fail, never a silent 100-cap."""
    doc = json.loads(body("window_json"), parse_float=str)
    doc["results"] = doc["results"][:-1]
    synthetic = json.dumps(doc).encode()
    with pytest.raises(ValueError, match="total_count|complete"):
        _window_source().parse(all_specs(), [_responses()[0],
                                             RawResponse(url=_responses()[1].url,
                                                         params=_responses()[1].params,
                                                         status=200, body=synthetic)])


@pytest.mark.parametrize("old,new,match", [
    (b'"license": "CC BY 4.0"', b'"license": "CC0 1.0"', "licen"),
    (b'"license_url": "https://creativecommons.org/licenses/by/4.0/"',
     b'"license_url": "https://example.com/x"', "licen"),
    (b'"label": "Market (kWh)"', b'"label": "Market (MWh)"', "label"),
    (b'"type": "datetime"', b'"type": "text"', "datahora"),
    (b'"publisher": "E-REDES"', b'"publisher": "REN"', "publisher"),
    (b'"dataset_id": "energia-produzida-total-nacional"',
     b'"dataset_id": "energia-produzida"', "dataset_id"),
])
def test_parse_rejects_metadata_drift(old, new, match):
    tampered = body("metadata").replace(old, new, 1)
    assert tampered != body("metadata")
    with pytest.raises(ValueError, match=match):
        _window_source().parse(all_specs(), [
            RawResponse(url=_responses()[0].url, params=None, status=200, body=tampered),
            _responses()[1]])


def test_parse_rejects_html_body():
    with pytest.raises(ValueError, match="markup"):
        _window_source().parse(all_specs(), _mutate_window(
            body("window_json"), b"<!DOCTYPE html><html><body>x</body></html>"))


# --- through the pipeline ----------------------------------------------------------------------

def test_full_pipeline_records_window_with_provenance(db, tmp_path):
    specs = all_specs()
    sync_registry(db, specs)
    store = RawStore(tmp_path / "raw")
    from datetime import datetime, timedelta, timezone

    class Clock:
        t = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)

        def __call__(self):
            self.t += timedelta(seconds=1)
            return self.t
    r = run_dataset(db, store, _window_source(), specs, FixtureHttp(), Clock())
    assert r.state == "pending-verification" and r.n_written == 288 and r.n_quarantined == 0
    rows = db.conn.execute(
        "SELECT period, value_text FROM observation WHERE series_id="
        "'eredes.production_market.PT' ORDER BY period").fetchall()
    assert len(rows) == 96
    assert rows[0] == ("2026-11-10T00:00:00+00:00", "925741.0")
    assert rows[-1] == ("2026-11-10T23:45:00+00:00", "1097652.0")
    # every response is archived evidence: the metadata record + the records page
    fetches = db.conn.execute("SELECT url, http_status, ok FROM raw_fetch").fetchall()
    assert len(fetches) == 2 and all(s == 200 and ok == 1 for _, s, ok in fetches)
    meta_row = db.conn.execute("SELECT raw_fetch_id FROM observation ORDER BY id LIMIT 1"
                               ).fetchone()[0]
    assert "/records" in db.conn.execute("SELECT url FROM raw_fetch WHERE id=?",
                                         (meta_row,)).fetchone()[0]
    served = db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0]
    assert served == 0  # pending-verification is never served


def test_pipeline_html_200_body_is_failed_fetch(db, tmp_path):
    specs = all_specs()
    sync_registry(db, specs)
    store = RawStore(tmp_path / "raw")
    html = FixtureHttp({"window_json": b"<!DOCTYPE html><html><body>err</body></html>"})
    r = run_dataset(db, store, _window_source(), specs, html)
    assert r.state == "failed-fetch" and r.n_written == 0
    kinds = db.conn.execute("SELECT kind FROM event").fetchall()
    assert ("fetch_failure",) in kinds
