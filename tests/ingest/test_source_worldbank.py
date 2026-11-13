"""World Bank API v2 source adapter tests — real recorded fixtures
(tests/ingest/fixtures/worldbank/, 2026-11-11, sha256-pinned by MANIFEST.json):
multi-geography one-page payloads (r5 GDP PT;ES;DE, population EU;GR;AT), paginated probes
(r1 page 1/14, r6 page 1/66) and pinned tokens cross-checked live against the publisher's
independent CSV ZIP channel (5/5 PT GDP pins 2021..2025, plus DE/ES pins)."""
import json

import pytest

from ingest.db import open_db
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources import RawResponse
from ingest.sources.worldbank import API_BASE, PER_PAGE, WorldBankSource, parse_native_code
from ingest.validate import validate
from tests.ingest.worldbank_fixtures import (
    GDP_PTDES,
    POP_EUGRAT,
    FixtureHttp,
    body,
    registry_specs,
    specs_of,
)

_GDP = "NY.GDP.MKTP.CD"
_POP = "SP.POP.TOTL"

# Pinned (series, period) -> publisher token read from the recorded bytes themselves.
PINS_R5 = {
    ("worldbank.gdp_usd.PT", "2025"): "346639825141.821",
    ("worldbank.gdp_usd.PT", "2020"): "229618773422.577",
    ("worldbank.gdp_usd.PT", "1961"): "3573719084.53354",
    ("worldbank.gdp_usd.ES", "2020"): "1289783836971.21",
    ("worldbank.gdp_usd.DE", "1961"): "96558204043.1028",  # 4-decimal token; never a float
    ("worldbank.gdp_usd.DE", "2025"): "5050922925047.05",
}
PINS_POP = {
    ("worldbank.population.EU", "1960"): "357710476",  # EU aggregate -> countryiso3code EUU
    ("worldbank.population.EU", "2025"): "451127411",
    ("worldbank.population.GR", "2025"): "10413962",
    ("worldbank.population.AT", "1990"): "7677850",
}


def _resp(file: str, url: str, params: dict | None = None, status: int = 200,
          body_: bytes | None = None) -> RawResponse:
    return RawResponse(url=url, params=params, status=status,
                       body=body_ if body_ is not None else body(file))


def _r5(params: dict | None = None, **kw) -> RawResponse:
    return _resp("r5-multicountry-json.json",
                 f"{API_BASE}/country/PT;ES;DE/indicator/{_GDP}",
                 params=params or {"format": "json", "per_page": str(PER_PAGE)}, **kw)


def _pop(params: dict | None = None, **kw) -> RawResponse:
    return _resp("multi-eugrat-pop.json",
                 f"{API_BASE}/country/EU;GR;AT/indicator/{_POP}",
                 params=params or {"format": "json", "per_page": str(PER_PAGE)}, **kw)


def test_parse_native_code_format():
    assert parse_native_code("NY.GDP.MKTP.CD:PRT") == ("NY.GDP.MKTP.CD", "PRT")
    for bad in (None, "", "PRT", "NY.GDP.MKTP.CD", ":PRT", "NY.GDP.MKTP.CD:", ":",
                "NY.GDP.MKTP.CD:PT", "ny.gdp.mktp.cd:PRT", "NY.GDP.MKTP.CD:PRT:extra"):
        with pytest.raises(ValueError):
            parse_native_code(bad)


def test_parse_fixture_yields_expected_rows():
    parsed = WorldBankSource().parse(specs_of(GDP_PTDES), [_r5()])
    for (sid, period), token in PINS_R5.items():
        rows = {r.period_raw: r.value_raw for r in parsed[sid]}
        assert rows[period] == token
    # 198 payload rows = 66 years x 3 geographies; every spec gets its 66 rows
    assert sum(len(rows) for rows in parsed.values()) == 198
    assert all(len(rows) == 66 for rows in parsed.values())


def test_parse_second_fixture_multiple_geographies_and_indicators():
    parsed = WorldBankSource().parse(specs_of(GDP_PTDES + POP_EUGRAT), [_r5(), _pop()])
    for (sid, period), token in {**PINS_R5, **PINS_POP}.items():
        rows = {r.period_raw: r.value_raw for r in parsed[sid]}
        assert rows[period] == token
    assert all(len(parsed[sid]) == 66 for sid in GDP_PTDES + POP_EUGRAT)


def test_tokens_are_publisher_strings_never_floats():
    parsed = WorldBankSource().parse(specs_of(GDP_PTDES), [_r5()])
    rows = [r for rows in parsed.values() for r in rows]
    assert all(type(r.value_raw) is str for r in rows)
    by = {(r_id, r.period_raw): r.value_raw
          for r_id, rows in parsed.items() for r in rows}
    assert by[("worldbank.gdp_usd.DE", "1961")] == "96558204043.1028"  # not 96558204043.10
    assert by[("worldbank.population.EU" if False else "worldbank.gdp_usd.PT", "2025")] == \
        "346639825141.821"  # not 346639825141.821044921875


def test_every_row_unit_absent_and_flag_normal():
    """Both series surfaces are empty strings in the archived bytes: unit_raw=None (absent,
    honestly), flag_raw='normal' by explicit declaration of the reviewed shape."""
    parsed = WorldBankSource().parse(specs_of(GDP_PTDES + POP_EUGRAT), [_r5(), _pop()])
    rows = [r for rows in parsed.values() for r in rows]
    assert {r.unit_raw for r in rows} == {None}
    assert {r.flag_raw for r in rows} == {"normal"}


def test_response_index_points_at_each_rows_response():
    parsed = WorldBankSource().parse(specs_of(GDP_PTDES + POP_EUGRAT), [_r5(), _pop()])
    assert {r.response_index for sid in GDP_PTDES for r in parsed[sid]} == {0}
    assert {r.response_index for sid in POP_EUGRAT for r in parsed[sid]} == {1}


def test_paginated_probe_page1_rows_have_response_index_and_consistent_meta():
    """r1 is a real page 1 of 14 (per_page=5 probe): parse accepts a well-formed partial page
    set (it does not invent the missing pages; fetch is what follows them)."""
    r = _resp("r1-pt-gdp-json.json", f"{API_BASE}/country/PT/indicator/{_GDP}",
              params={"format": "json", "per_page": "5"})
    parsed = WorldBankSource().parse(specs_of(["worldbank.gdp_usd.PT"]), [r])
    rows = {row.period_raw: row.value_raw for row in parsed["worldbank.gdp_usd.PT"]}
    assert rows == {"2025": "346639825141.821", "2024": "313656884870.859",
                    "2023": "292323800948.839", "2022": "256898677175.024",
                    "2021": "256055879091.139"}


def test_parse_html_error_page_raises():
    with pytest.raises(ValueError, match="markup|HTML"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(
            body_=b"<!DOCTYPE html><html><body>World Bank</body></html>")])


def test_parse_rejects_bad_json():
    with pytest.raises(ValueError, match="JSON"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=b'[{"page":1,')])


def test_parse_rejects_api_error_json():
    """The publisher's error shape (a 'message' list instead of [meta, rows]) fails closed."""
    err = b'[{"message":[{"id":"120","key":"Invalid value","value":"The indicator is invalid"}]}]'
    with pytest.raises(ValueError, match="error|message|shape"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=err)])


def test_parse_rejects_non_2xx_responses():
    for status in (301, 400, 403, 404, 500):
        with pytest.raises(ValueError, match=f"HTTP {status}"):
            WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(status=status)])


def test_parse_rejects_duplicate_json_keys():
    tampered = body("r5-multicountry-json.json").replace(
        b'"sourceid":"2"', b'"sourceid":"2","sourceid":"2"', 1)
    with pytest.raises(ValueError, match="duplicate"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_quoted_number_token_raises_even_when_numeric_shaped():
    """value must be a genuine JSON number; a quoted "346639825141.821" is a type flip on the
    publisher token (would still Decimal-verify 1:1) and must fail closed."""
    tampered = body("r5-multicountry-json.json").replace(
        b'"value":346639825141.821', b'"value":"346639825141.821"', 1)
    with pytest.raises(ValueError, match="number token"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_numeric_identity_label_raises():
    """countryiso3code / indicator.id are identity labels: a JSON number is not a label."""
    tampered = body("r5-multicountry-json.json").replace(b'"countryiso3code":"DEU"',
                                                         b'"countryiso3code":276', 1)
    with pytest.raises(ValueError, match="countryiso3code"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_malformed_period_raises():
    tampered = body("r5-multicountry-json.json").replace(b'"date":"2025"', b'"date":"20X5"', 1)
    with pytest.raises(ValueError, match="date"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_unexpected_country_raises_not_silent_remap():
    tampered = body("r5-multicountry-json.json").replace(b'"countryiso3code":"DEU"',
                                                         b'"countryiso3code":"FRA"', 1)
    with pytest.raises(ValueError, match="countryiso3code|geography"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_country_id_must_match_registry_geography():
    """country.id (publisher ISO2) must equal the registry geography of the matched series:
    a payload claiming PRT rows under country.id 'ES' is an identity anomaly, fail closed."""
    tampered = body("r5-multicountry-json.json").replace(
        b'"country":{"id":"PT","value":"Portugal"}', b'"country":{"id":"ES","value":"Portugal"}', 1)
    with pytest.raises(ValueError, match="country"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_unexpected_indicator_raises():
    tampered = body("r5-multicountry-json.json").replace(b'"id":"NY.GDP.MKTP.CD"',
                                                         b'"id":"NY.GDP.PCAP.CD"', 1)
    with pytest.raises(ValueError, match="indicator"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_duplicate_row_identity_raises():
    """The same (indicator, iso3, date) twice in one payload is an unarbitratable anomaly."""
    b5 = body("r5-multicountry-json.json")
    head = b'[{"page":1,"pages":1,"per_page":20000,"total":198,"sourceid":"2",' \
           b'"lastupdated":"2026-11-11"},['
    sep = b'},{"indicator"'
    pieces = b5[len(head):-2].split(sep)
    assert len(pieces) == 198
    dup = pieces[0][len(b'{"indicator"'):]  # separator supplies the leading '{"indicator"'
    tampered = (head + sep.join([pieces[0]] + [dup] + pieces[1:]) + b']]').replace(
        b'"total":198', b'"total":199', 1)  # meta consistent so the IDENTITY guard fires
    assert len(json.loads(tampered)[1]) == 199  # row 0 twice
    with pytest.raises(ValueError, match="duplicate"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_missing_declared_row_raises():
    """meta total=198 but only 197 rows arrive: truncation fails closed on the page counts."""
    b5 = body("r5-multicountry-json.json")
    head = b'[{"page":1,"pages":1,"per_page":20000,"total":198,"sourceid":"2",' \
           b'"lastupdated":"2026-11-11"},['
    pieces = b5[len(head):-2].split(b'},{"indicator"')
    # drop the last row: pieces[k] (k<last) lacks its trailing '}' (carried by the separator)
    tampered = head + b'},{"indicator"'.join(pieces[:-1]) + b'}]]'
    assert len(json.loads(tampered)[1]) == 197
    with pytest.raises(ValueError, match="total|truncat|198|rows"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_page_meta_inconsistency_raises():
    tampered = body("r5-multicountry-json.json").replace(b'"pages":1', b'"pages":2', 1)
    with pytest.raises(ValueError, match="page"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])


def test_nonempty_unit_or_status_is_an_unknown_surface_and_raises():
    """Series surfaces observed empty in evidence; a non-empty unit/obs_status is an unreviewed
    vocabulary (never silently remapped to a label of ours)."""
    with pytest.raises(ValueError, match="unit"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=body(
            "r5-multicountry-json.json").replace(b'"unit":""', b'"unit":"US$"', 1))])
    with pytest.raises(ValueError, match="status"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=body(
            "r5-multicountry-json.json").replace(b'"obs_status":""', b'"obs_status":"E"', 1))])


def test_unrequested_indicator_response_raises():
    with pytest.raises(ValueError, match="indicator|unrequested"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_pop()])


def test_url_indicator_must_match_payload_indicator():
    """Rows self-identify (indicator/countryiso3code); the response URL's indicator must agree
    with the payload rows — a channel that answers a different indicator than it claims to is
    identity drift, fail closed."""
    body5 = body("r5-multicountry-json.json")
    with pytest.raises(ValueError, match="URL"):
        WorldBankSource().parse(specs_of(GDP_PTDES + POP_EUGRAT), [_resp(
            "r5-multicountry-json.json", f"{API_BASE}/country/EU;GR;AT/indicator/{_POP}",
            body_=body5)])
    # and an empty payload page for an indicator with no requested series is not silently kept
    empty = b'[{"page":1,"pages":1,"per_page":20000,"total":0,"sourceid":"2",' \
            b'"lastupdated":"2026-11-11"},null]'
    with pytest.raises(ValueError, match="unrequested"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_resp(
            "r5-multicountry-json.json", f"{API_BASE}/country/PT;ES;DE/indicator/{_POP}",
            body_=empty)])


def test_unexpected_url_shape_raises():
    with pytest.raises(ValueError, match="URL"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [_resp(
            "r5-multicountry-json.json", "https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.CD")])


def test_duplicate_native_code_specs_rejected():
    s = specs_of(["worldbank.gdp_usd.PT"])[0]
    twin = s.model_copy(update={"id": "worldbank.gdp_usd.PT_twin"})
    with pytest.raises(ValueError, match="duplicate native_code"):
        WorldBankSource().parse([s, twin], [_r5()])


def _two_pages() -> tuple[bytes, bytes]:
    """Split the REAL r5 rows into two well-formed pages, byte-preserving every row."""
    b5 = body("r5-multicountry-json.json")
    head = b'[{"page":1,"pages":1,"per_page":20000,"total":198,"sourceid":"2",' \
           b'"lastupdated":"2026-11-11"},['
    assert b5.startswith(head) and b5.endswith(b']]')
    pieces = b5[len(head):-2].split(b'},{"indicator"')
    assert len(pieces) == 198
    meta1 = b'{"page":1,"pages":2,"per_page":100,"total":198,"sourceid":"2",' \
            b'"lastupdated":"2026-11-11"}'
    meta2 = b'{"page":2,"pages":2,"per_page":100,"total":198,"sourceid":"2",' \
            b'"lastupdated":"2026-11-11"}'
    join = b'},{"indicator"'
    page1 = b'[' + meta1 + b',[' + join.join(pieces[:100]) + b'}]]'
    page2 = b'[' + meta2 + b',[{"indicator"' + join.join(pieces[100:]) + b']]'
    assert len(json.loads(page1)[1]) == 100 and len(json.loads(page2)[1]) == 98
    return page1, page2


def test_parse_two_page_response_set_yields_all_rows_with_indices():
    p1, p2 = _two_pages()
    r1 = _r5(body_=p1, params={"format": "json", "per_page": "100"})
    r2 = _r5(body_=p2, params={"format": "json", "per_page": "100", "page": "2"})
    parsed = WorldBankSource().parse(specs_of(GDP_PTDES), [r1, r2])
    for (sid, period), token in PINS_R5.items():
        rows = {r.period_raw: r.value_raw for r in parsed[sid]}
        assert rows[period] == token
    assert sum(len(rows) for rows in parsed.values()) == 198
    idx = {sid: sorted({r.response_index for r in rows}) for sid, rows in parsed.items()}
    # payload order is DE rows 0..65, ES 66..131, PT 132..197: the page break at 100 leaves DE
    # fully on page 1, PT fully on page 2, and ES spanning both.
    assert idx == {"worldbank.gdp_usd.DE": [0], "worldbank.gdp_usd.ES": [0, 1],
                   "worldbank.gdp_usd.PT": [1]}


def test_parse_duplicate_page_rejected():
    p1, _ = _two_pages()
    r1 = _r5(body_=p1, params={"format": "json", "per_page": "100"})
    with pytest.raises(ValueError, match="page"):
        WorldBankSource().parse(specs_of(GDP_PTDES), [r1, r1])


def test_parse_page1_of2_without_page2_still_parses_what_arrived():
    """parse() maps what it is given; completeness of the pagination is fetch()'s job (it
    declares pages and any missing page means a mid-stream failure already) — but the meta of
    EACH response must still be internally consistent."""
    p1, _ = _two_pages()
    parsed = WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=p1)])
    assert sum(len(rows) for rows in parsed.values()) == 100


def test_null_value_cells_become_none_not_zero_and_not_dropped():
    tampered = body("r5-multicountry-json.json").replace(b'"value":346639825141.821',
                                                         b'"value":null', 1)
    parsed = WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])
    row = [r for r in parsed["worldbank.gdp_usd.PT"] if r.period_raw == "2025"][0]
    assert row.value_raw is None
    obs, rej = validate(registry_specs()["worldbank.gdp_usd.PT"], parsed["worldbank.gdp_usd.PT"])
    assert len(obs) == 65 and len(rej) == 1 and rej[0].reason == "non_numeric"


def test_scientific_notation_token_is_preserved_then_quarantined_by_validation():
    """A genuine JSON number 1.234e8 is preserved verbatim as '1.234e8' (never reformatted);
    the existing validator (no exponent grammar) quarantines it non_numeric — reported, not
    silently normalized to fixed point."""
    tampered = body("r5-multicountry-json.json").replace(b'"value":346639825141.821',
                                                         b'"value":3.46639825141821e11', 1)
    parsed = WorldBankSource().parse(specs_of(GDP_PTDES), [_r5(body_=tampered)])
    row = [r for r in parsed["worldbank.gdp_usd.PT"] if r.period_raw == "2025"][0]
    assert row.value_raw == "3.46639825141821e11"
    obs, rej = validate(registry_specs()["worldbank.gdp_usd.PT"], parsed["worldbank.gdp_usd.PT"])
    assert rej[0].period_raw == "2025" and rej[0].reason == "non_numeric" and len(obs) == 65


def test_validate_roundtrip_on_real_fixtures():
    specs = specs_of(GDP_PTDES + POP_EUGRAT)
    parsed = WorldBankSource().parse(specs, [_r5(), _pop()])
    by_id = {s.id: s for s in specs}
    for sid, rows in parsed.items():
        obs, rej = validate(by_id[sid], rows)
        assert not rej, (sid, rej[:3])
        assert len(obs) == 66
        assert {o.status_flag for o in obs} == {"normal"}
        assert {o.period for o in obs} == {str(y) for y in range(1960, 2026)}


def test_fetch_requests_one_page_per_indicator_with_all_registry_geographies():
    http = FixtureHttp()
    out = list(WorldBankSource().fetch(specs_of(GDP_PTDES + POP_EUGRAT), http))
    assert len(out) == 2  # 2 indicators x 1 page
    assert http.calls == [(_GDP, frozenset({"PT", "ES", "DE"}), 1),
                          (_POP, frozenset({"EU", "GR", "AT"}), 1)]
    assert all(r.status == 200 and r.body for r in out)
    assert all(u.startswith(f"{API_BASE}/country/") and "/indicator/" in u
               for u in (r.url for r in out))


def test_fetch_follows_declared_pagination():
    p1, p2 = _two_pages()

    class TwoPageHttp(FixtureHttp):
        def get(self, url, params=None, headers=None, timeout=None):
            page = int((params or {}).get("page", "1"))
            key = (_GDP, frozenset({"PT", "ES", "DE"}), page)
            self.calls.append(key)
            from ingest.http import HttpResult
            return HttpResult(status=200, body=p1 if page == 1 else p2,
                              url=f"{API_BASE}/country/DE;ES;PT/indicator/{_GDP}")

    http = TwoPageHttp()
    out = list(WorldBankSource().fetch(specs_of(GDP_PTDES), http))
    assert [c[2] for c in http.calls] == [1, 2]
    assert len(out) == 2


def test_fetch_raises_on_unreadable_meta():
    class Junk(FixtureHttp):
        def get(self, url, params=None, headers=None, timeout=None):
            from ingest.http import HttpResult
            return HttpResult(status=200, body=b"<html>nope</html>",
                              url="https://api.worldbank.org/x")

    with pytest.raises(ValueError):
        list(WorldBankSource().fetch(specs_of(GDP_PTDES), Junk()))


def test_fetch_yields_non2xx_for_the_pipeline_to_classify_without_retry_or_filter():
    http = FixtureHttp(status={(_GDP, frozenset({"PT", "ES", "DE"}), 1): 404})
    out = list(WorldBankSource().fetch(specs_of(GDP_PTDES), http))
    assert [r.status for r in out] == [404]  # yielded as-is, no exception


def test_pipeline_run_on_fixtures_writes_and_links_provenance(tmp_path):
    specs = specs_of(GDP_PTDES + POP_EUGRAT)
    db = open_db(tmp_path / "t.db")
    try:
        sync_registry(db, specs)
        r = run_dataset(db, RawStore(tmp_path / "raw"), WorldBankSource(), specs, FixtureHttp())
        assert r.state == "pending-verification"
        assert r.n_written == 6 * 66 == 396
        assert r.n_quarantined == 0
        rows = db.conn.execute(
            "SELECT series_id, COUNT(*), MIN(period), MAX(period) FROM observation "
            "GROUP BY series_id ORDER BY series_id").fetchall()
        assert [(sid, n, lo, hi) for sid, n, lo, hi in rows] == [
            (sid, 66, "1960", "2025") for sid in sorted(GDP_PTDES + POP_EUGRAT)]
        # provenance: observations link back to their raw_fetch response (2 recorded ones)
        assert db.conn.execute("SELECT COUNT(*) FROM raw_fetch WHERE ok=1").fetchone()[0] == 2
        assert {x[0] for x in db.conn.execute(
            "SELECT DISTINCT raw_fetch_id FROM observation").fetchall()} == {1, 2}
    finally:
        db.close()


def test_registry_native_codes_complete():
    reg = registry_specs()
    assert len(reg) == 982
    for s in reg.values():
        code, iso3 = parse_native_code(s.native_code)  # raises unless '<CODE>:<ISO3>'
        assert s.url == f"{API_BASE}/country/{iso3}/indicator/{code}"


def test_active_native_codes_are_unique():
    codes = [s.native_code for s in registry_specs().values() if s.active]
    assert len(codes) == 930
    assert len(codes) == len(set(codes))
