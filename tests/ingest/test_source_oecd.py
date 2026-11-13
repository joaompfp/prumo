"""OECD SDMX-JSON data 2.0 source adapter tests - real recorded fixtures
(tests/ingest/fixtures/oecd/, 2026-11-12 f3nix, sha256-pinned by MANIFEST.json; byte-identical
copies of the controller-rehashed Task 15 discovery items 1,3,5,7,9,11).

The six active core monthly PT series share one collector request shape:
    GET https://sdmx.oecd.org/public/rest/data/<agency>,<dataflow>/<key>[?startPeriod=YYYY-MM
        &endPeriod=YYYY-MM]  with header Accept: application/vnd.sdmx.data+json;version=2.0

Every fixture's TIME_PERIOD values array is UNSORTED (index->period mapping is exercised, never
zip-sorted), values are genuine JSON number primitives (trailing-zero tokens '-6.0', '12.0',
'6.0' preserved verbatim - the Part B CSV verifier channel formats them '-6', '12', '6'), and
all 77 observations carry OBS_STATUS=A ('Normal value', mapped to flag 'normal'; any other code
fails closed - the full OBS_STATUS codelist was NOT enumerable, Task 15 discovery item 13).
"""
import pytest

from ingest.db import open_db
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources import RawResponse
from ingest.sources.oecd import API_BASE, OecdSource, parse_native_code
from ingest.validate import validate
from tests.ingest.oecd_fixtures import (
    ALL_SIX,
    FIX,
    JSON_BY_NATIVE_CODE,
    MANIFEST,
    FixtureHttp,
    body,
    registry_specs,
    specs_of,
)

NC = {  # series id -> native_code (pinned coordinates, Task 15 discovery §2)
    "oecd.cli.PT": "OECD.SDD.STES,DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z.H",
    "oecd.employment.PT": "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.EM.PB.C.Y._Z.FT.N",
    "oecd.order_books.PT": "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.OB.PB.C.Y._Z.C.N",
    "oecd.production.PT": "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.PR.PB.C.Y._Z.T.N",
    "oecd.selling_prices.PT": "OECD.SDD.STES,DSD_STES@DF_BTS/PRT.M.SP.PB.C.Y._Z.FT.N",
    "oecd.unemp_m.PT": "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M/"
                       "PRT.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M",
}
FILE_OF = {sid: JSON_BY_NATIVE_CODE[nc] for sid, nc in NC.items()}

# Named publisher values read from the recorded bytes themselves (discovery §4 cross-checked
# them live against the independent CSV channel; '->' marks trailing-zero tokens).
PINS = {
    ("oecd.cli.PT", "2025-10"): "99.94156",
    ("oecd.cli.PT", "2025-12"): "100.321",
    ("oecd.cli.PT", "2026-01"): "100.2026",
    ("oecd.cli.PT", "2026-04"): "99.83678",  # 5 dp despite DECIMALS=2 (display hint only)
    ("oecd.cli.PT", "2026-10"): "99.80521",
    ("oecd.employment.PT", "2026-01"): "4.1",
    ("oecd.employment.PT", "2026-02"): "3.4",
    ("oecd.employment.PT", "2026-05"): "-6.0",  # -> CSV '-6'
    ("oecd.employment.PT", "2026-08"): "-4.4",
    ("oecd.employment.PT", "2026-10"): "-5.7",
    ("oecd.order_books.PT", "2025-10"): "-12.5",
    ("oecd.order_books.PT", "2026-01"): "-12.0",  # -> CSV '-12'
    ("oecd.order_books.PT", "2026-03"): "-13.4",
    ("oecd.order_books.PT", "2026-08"): "-10.0",  # -> CSV '-10'
    ("oecd.order_books.PT", "2026-09"): "-14.0",  # -> CSV '-14'
    ("oecd.production.PT", "2025-10"): "1.4",
    ("oecd.production.PT", "2026-01"): "3.8",
    ("oecd.production.PT", "2026-02"): "-7.9",
    ("oecd.production.PT", "2026-04"): "-1.1",
    ("oecd.production.PT", "2026-10"): "-2.2",
    ("oecd.selling_prices.PT", "2025-10"): "5.1",
    ("oecd.selling_prices.PT", "2025-12"): "10.7",
    ("oecd.selling_prices.PT", "2026-01"): "12.0",  # -> CSV '12'
    ("oecd.selling_prices.PT", "2026-05"): "28.4",
    ("oecd.selling_prices.PT", "2026-09"): "22.4",
    ("oecd.unemp_m.PT", "2025-10"): "5.8",
    ("oecd.unemp_m.PT", "2026-01"): "5.8",
    ("oecd.unemp_m.PT", "2026-02"): "6.0",  # -> CSV '6'
    ("oecd.unemp_m.PT", "2026-07"): "5.7",
    ("oecd.unemp_m.PT", "2026-09"): "5.6",
}
# The COMPLETE decoded content of the six archives (77 observations).
EXPECTED = {
    "oecd.cli.PT": dict([
        ("2025-10", "99.94156"), ("2025-11", "100.2412"), ("2025-12", "100.321"),
        ("2026-01", "100.2026"), ("2026-02", "100.1511"), ("2026-03", "100.0558"),
        ("2026-04", "99.83678"), ("2026-05", "99.67718"), ("2026-06", "99.61328"),
        ("2026-07", "99.58485"), ("2026-08", "99.581"), ("2026-09", "99.66871"),
        ("2026-10", "99.80521")]),
    "oecd.employment.PT": dict([
        ("2025-10", "3.3"), ("2025-11", "1.6"), ("2025-12", "-5.5"), ("2026-01", "4.1"),
        ("2026-02", "3.4"), ("2026-03", "1.5"), ("2026-04", "1.6"), ("2026-05", "-6.0"),
        ("2026-06", "1.6"), ("2026-07", "3.3"), ("2026-08", "-4.4"), ("2026-09", "2.5"),
        ("2026-10", "-5.7")]),
    "oecd.order_books.PT": dict([
        ("2025-10", "-12.5"), ("2025-11", "-9.0"), ("2025-12", "-10.5"),
        ("2026-01", "-12.0"), ("2026-02", "-13.6"), ("2026-03", "-13.4"),
        ("2026-04", "-9.8"), ("2026-05", "-11.4"), ("2026-06", "-10.7"),
        ("2026-07", "-12.5"), ("2026-08", "-10.0"), ("2026-09", "-14.0"),
        ("2026-10", "-13.2")]),
    "oecd.production.PT": dict([
        ("2025-10", "1.4"), ("2025-11", "-2.5"), ("2025-12", "-4.9"), ("2026-01", "3.8"),
        ("2026-02", "-7.9"), ("2026-03", "-5.2"), ("2026-04", "-1.1"), ("2026-05", "-1.3"),
        ("2026-06", "-3.2"), ("2026-07", "-1.9"), ("2026-08", "-2.8"), ("2026-09", "-2.8"),
        ("2026-10", "-2.2")]),
    "oecd.selling_prices.PT": dict([
        ("2025-10", "5.1"), ("2025-11", "8.8"), ("2025-12", "10.7"), ("2026-01", "12.0"),
        ("2026-02", "7.8"), ("2026-03", "23.4"), ("2026-04", "27.8"), ("2026-05", "28.4"),
        ("2026-06", "16.6"), ("2026-07", "10.9"), ("2026-08", "13.3"), ("2026-09", "22.4"),
        ("2026-10", "15.7")]),
    "oecd.unemp_m.PT": dict([
        ("2025-10", "5.8"), ("2025-11", "5.7"), ("2025-12", "5.7"), ("2026-01", "5.8"),
        ("2026-02", "6.0"), ("2026-03", "5.9"), ("2026-04", "5.7"), ("2026-05", "5.6"),
        ("2026-06", "5.7"), ("2026-07", "5.7"), ("2026-08", "5.6"), ("2026-09", "5.6")]),
}
assert set(PINS) <= {(sid, p) for sid, d in EXPECTED.items() for p in d}


def _resp(sid: str, status: int = 200, body_: bytes | None = None,
          params: dict | None = None, url: str | None = None) -> RawResponse:
    """An archived response: URL = base + adapter-encoded params (what a client produces)."""
    from urllib.parse import urlencode
    p = params if params is not None else {"startPeriod": "2025-10"}
    u = url or f"{API_BASE}/data/{NC[sid]}" + (f"?{urlencode(p)}" if p else "")
    return RawResponse(url=u, params=p, status=status,
                       body=body_ if body_ is not None else body(FILE_OF[sid]))


def _six_responses() -> list[RawResponse]:
    return [_resp(sid) for sid in ALL_SIX]


def _parse(sids: list[str], responses: list[RawResponse]) -> dict:
    return OecdSource().parse(specs_of(sids), responses)


def test_parse_native_code_format():
    assert parse_native_code(NC["oecd.cli.PT"]) == (
        "OECD.SDD.STES", "DSD_STES@DF_CLI", "PRT.M.BCICP.IX._Z.AA.IX._Z.H")
    assert parse_native_code(NC["oecd.unemp_m.PT"]) == (
        "OECD.SDD.TPS", "DSD_LFS@DF_IALFS_UNE_M", "PRT.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M")
    for bad in (None, "", "DF_CLI", "PRT.M.BCICP.IX._Z.AA.IX._Z.H",
                "DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z.H",  # missing agency
                "OECD.SDD.STES/PRT.M.BCICP.IX._Z.AA.IX._Z.H",  # dataflow without DSD@DF shape
                "OECD.SDD.STES,DSD_STES@DF_CLI",  # missing key
                "OECD.SDD.STES,DSD_STES@DF_CLI/",  # empty key
                "OECD.SDD.STES,DSD_STES@DF_CLI/PRT..M",  # empty segment
                "oecd.sdd.stes,DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z.H",  # lowercase
                "OECD.SDD.STES,DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z.H/extra",
                ):
        with pytest.raises(ValueError):
            parse_native_code(bad)


def test_parse_six_fixtures_yield_every_publisher_token():
    parsed = _parse(ALL_SIX, _six_responses())
    for sid, expected in EXPECTED.items():
        rows = {r.period_raw: r.value_raw for r in parsed[sid]}
        assert rows == expected, sid  # the COMPLETE archive content, not a sample
        assert all(PINS[(s, p)] == rows[p] for (s, p) in PINS if s == sid)
    assert sum(len(rows) for rows in parsed.values()) == 77


def test_tokens_are_publisher_number_tokens_never_floats():
    parsed = _parse(ALL_SIX, _six_responses())
    rows = {r.period_raw: r.value_raw for r in parsed["oecd.employment.PT"]}
    assert rows["2026-05"] == "-6.0" and type(rows["2026-05"]) is str  # not -6 / -6.0 float
    rows = {r.period_raw: r.value_raw for r in parsed["oecd.selling_prices.PT"]}
    assert rows["2026-01"] == "12.0"  # not 12
    rows = {r.period_raw: r.value_raw for r in parsed["oecd.cli.PT"]}
    assert rows["2026-04"] == "99.83678"  # 5 dp token; DECIMALS=2 never truncates
    all_rows = [r for rows in parsed.values() for r in rows]
    assert all(type(r.value_raw) is str for r in all_rows)
    assert all(r.unit_raw is None for r in all_rows)  # row-level unit: absent by design
    assert {r.flag_raw for r in all_rows} == {"normal"}  # OBS_STATUS=A only


def test_unsorted_time_period_values_are_mapped_by_index_not_sort_order():
    """Every fixture's TIME_PERIOD values array descends (2026-02 first on CLI): a parser that
    zip-sorted would silently reattach values to wrong periods; map via the actual values[i]."""
    import json as _json
    doc = _json.loads(body(FILE_OF["oecd.cli.PT"]))
    tp = [v["id"] for v in doc["data"]["structures"][0]["dimensions"]["observation"][0]["values"]]
    assert tp != sorted(tp) and tp[0] == "2026-02"  # the fixture really is unsorted
    parsed = _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT")])
    rows = {(r.period_raw, r.value_raw) for r in parsed["oecd.cli.PT"]}
    assert ("2026-02", "100.1511") in rows  # observation index '0' is the FIRST tp value entry
    assert ("2026-01", "100.2026") in rows  # and index '12' the LAST entry, not the first
    assert len(rows) == 13


def test_every_row_carries_its_own_response_index():
    parsed = _parse(ALL_SIX, _six_responses())
    for i, sid in enumerate(ALL_SIX):
        assert {r.response_index for r in parsed[sid]} == {i}, sid


def test_parse_html_error_page_raises():
    with pytest.raises(ValueError, match="markup|HTML"):
        _parse(["oecd.cli.PT"], [_resp(
            "oecd.cli.PT", body_=b"<!DOCTYPE html><html><body>OECD error</body></html>")])


def test_parse_rejects_bad_json():
    with pytest.raises(ValueError, match="JSON"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b'{"meta": {"schema":')])


def test_parse_rejects_duplicate_json_keys():
    b = body(FILE_OF["oecd.cli.PT"])
    tampered = b.replace(b'"test": false,', b'"test": false, "test": false,', 1)
    assert tampered != b
    with pytest.raises(ValueError, match="duplicate"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=tampered)])


def test_parse_rejects_non_2xx_responses():
    for status in (301, 400, 403, 404, 500):
        with pytest.raises(ValueError, match=f"HTTP {status}"):
            _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", status=status)])


def test_quoted_numeric_value_raises():
    """Observation values must be genuine JSON numbers; a quoted '100.1511' is a type flip on
    the publisher token (it would still Decimal-match the CSV channel) and fails closed."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b"100.1511") == 1
    with pytest.raises(ValueError, match="number"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b"100.1511,", b'"100.1511",', 1))])


def test_null_value_becomes_none_and_is_quarantined_not_dropped():
    b = body(FILE_OF["oecd.cli.PT"])
    tampered = b.replace(b"100.1511,", b"null,", 1)
    parsed = _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=tampered)])
    row = [r for r in parsed["oecd.cli.PT"] if r.period_raw == "2026-02"][0]
    assert row.value_raw is None
    obs, rej = validate(registry_specs()["oecd.cli.PT"], parsed["oecd.cli.PT"])
    assert len(obs) == 12 and len(rej) == 1 and rej[0].reason == "non_numeric"


def test_observation_index_must_be_canonical_ascii_decimal():
    """'00' and fullwidth '１２' alias genuine cells: aliases must never normalize onto a real
    index (a duplicate cell could then silently overwrite)."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"0": [\r\n') == 1
    with pytest.raises(ValueError, match="index"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"0": [\r\n', b'"00": [\r\n', 1))])
    assert b.count(b'"12": [\r\n') == 1
    with pytest.raises(ValueError, match="index"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"12": [\r\n', '"１２": [\r\n'.encode(), 1))])


def test_observation_index_out_of_range_raises():
    b = body(FILE_OF["oecd.cli.PT"])
    with pytest.raises(ValueError, match="index"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"12": [\r\n', b'"13": [\r\n', 1))])


def test_unknown_obs_status_fails_closed_not_guessed():
    """Only OBS_STATUS=A ('Normal value') exists in the archived evidence; the full codelist was
    NOT enumerated (discovery item 13, HTTP 404). Any other code fails closed."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"id": "A",') == 1
    with pytest.raises(ValueError, match="OBS_STATUS|status"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"id": "A",', b'"id": "E",', 1))])


def test_observation_attribute_index_out_of_range_raises():
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b"100.1511,\r\n                0\r\n") == 1
    with pytest.raises(ValueError, match="attribute"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b"100.1511,\r\n                0\r\n", b"100.1511,\r\n                1\r\n", 1))])


def test_unit_mult_other_than_0_fails_closed():
    """UNIT_MULT=0 ('Units') in every fixture; any other multiplier is a wrong scale, never a
    reason to convert or guess."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"id": "0",') == 1  # the UNIT_MULT value id
    with pytest.raises(ValueError, match="UNIT_MULT"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"id": "0",', b'"id": "6",', 1))])


def test_pinned_coordinate_drift_raises():
    """The payload series dimensions must resolve to exactly the requested key pins: here the
    payload swears the REF_AREA is France while the request pinned Portugal."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"id": "PRT",') == 1
    with pytest.raises(ValueError, match="identity|pin|drift"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"id": "PRT",', b'"id": "FRA",', 1))])


def test_measure_drift_li_vs_bcicp_raises():
    """DF_CLI's DEFAULT annotation is MEASURE=LI but oecd.cli.PT is pinned to BCICP (composite
    business confidence, NOT the headline leading indicator): defaulting would silently serve
    the wrong series."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"id": "BCICP",') == 1
    with pytest.raises(ValueError, match="identity|pin|drift"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"id": "BCICP",', b'"id": "LI",', 1))])


def test_registry_key_with_wrong_pin_count_is_rejected_before_any_http():
    """F1/F2 (Part A review probes P4/P5): every reviewed flow pins exactly 9 series
    dimensions. An EXTRA registry pin asserted nothing (silently unasserted identity, the
    fail-open class the BCICP/LI pin exists to kill) and a SHORT key left a raw IndexError
    escaping the adapter's error contract. The grammar now rejects both before any request."""
    for bad in (NC["oecd.cli.PT"] + ".X",  # 10 pins (extra)
                "OECD.SDD.STES,DSD_STES@DF_CLI/PRT.M.BCICP.IX._Z.AA.IX._Z",  # 8 pins (short)
                NC["oecd.unemp_m.PT"] + "._Z"):
        with pytest.raises(ValueError, match="9"):
            parse_native_code(bad)
    s = registry_specs()["oecd.cli.PT"].model_copy(
        update={"native_code": NC["oecd.cli.PT"] + ".X"})
    http = FixtureHttp()
    with pytest.raises(ValueError, match="9"):
        list(OecdSource().fetch([s], http))
    assert http.calls == []  # fail closed BEFORE the wire


def test_archived_url_with_wrong_pin_count_fails_closed_offline():
    """Offline identity comes from the archived URL: a 10-pin archived request identity can
    never be a reviewed series."""
    u = f"{API_BASE}/data/{NC['oecd.cli.PT']}.X?startPeriod=2025-10"
    with pytest.raises(ValueError, match="9"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", url=u)])


def test_payload_asserts_key_pin_count_against_dimension_count():
    """F1/F2 defense in depth: _payload itself asserts the requested key pin count equals the
    payload's series dimension count - an extra pin raises (pre-fix it parsed silently),
    a short key raises the module ValueError (pre-fix a raw IndexError escaped), and an
    unreviewed dataflow fails closed."""
    from ingest.sources.oecd import _payload
    agency, dataflow, key = parse_native_code(NC["oecd.cli.PT"])
    b = body(FILE_OF["oecd.cli.PT"])
    with pytest.raises(ValueError, match="dimension"):
        _payload(b, agency, dataflow, key + ".X", "probe")
    with pytest.raises(ValueError, match="dimension"):
        _payload(b, agency, dataflow, key.rsplit(".", 1)[0], "probe")
    # unreviewed flow fails closed even when the payload's dataflow URN is mutated to match
    urn = b"OECD.SDD.STES:DSD_STES@DF_CLI("
    assert b.count(urn) == 1
    with pytest.raises(ValueError, match="dataflow"):
        _payload(b.replace(urn, b"OECD.SDD.STES:DSD_STES@DF_OTHER(", 1),
                 agency, "DSD_STES@DF_OTHER", key, "probe")


def test_series_dimension_id_rename_fails_closed():
    """F3 (probe P3): payload series dimension ids must equal the reviewed per-dataflow
    sequence in keyPosition order - renaming MEASURE to MEASUREE silently rebased identity
    semantics and still parsed pre-fix."""
    for sid in ("oecd.cli.PT", "oecd.unemp_m.PT"):
        b = body(FILE_OF[sid])
        assert b.count(b'"id": "MEASURE",') == 1
        with pytest.raises(ValueError, match="dimension id"):
            _parse([sid], [_resp(sid, body_=b.replace(
                b'"id": "MEASURE",', b'"id": "MEASUREE",', 1))])


def test_series_dimension_id_duplicate_fails_closed():
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"id": "FREQ",') == 1
    with pytest.raises(ValueError, match="dimension id"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"id": "FREQ",', b'"id": "MEASURE",', 1))])


def test_series_dimension_position_drift_fails_closed():
    """Same id set, wrong keyPosition order (REF_AREA<->FREQ swap): position drift is a format
    change, never a re-parse."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"id": "REF_AREA",') == 1 and b.count(b'"id": "FREQ",') == 1
    t = b.replace(b'"id": "REF_AREA",', b'"id": "__TMP__",', 1)
    t = t.replace(b'"id": "FREQ",', b'"id": "REF_AREA",', 1)
    t = t.replace(b'"id": "__TMP__",', b'"id": "FREQ",', 1)
    with pytest.raises(ValueError, match="dimension id"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=t)])


def test_dataflow_urn_must_match_the_request_identity():
    b = body(FILE_OF["oecd.cli.PT"])
    urn = b"urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=OECD.SDD.STES:DSD_STES@DF_CLI(4.1)"
    assert b.count(urn) == 1
    with pytest.raises(ValueError, match="urn|Dataflow"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            urn, urn.replace(b"DF_CLI", b"DF_BTS"), 1))])


def test_structure_index_must_be_a_genuine_numeric_primitive():
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"structure": 0,') == 1
    with pytest.raises(ValueError, match="structure"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"structure": 0,', b'"structure": "0",', 1))])


def test_key_position_must_be_a_genuine_numeric_primitive():
    """Metadata ordering indices are JSON numbers in evidence; a quoted alias is tampering."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"keyPosition": 0,') == 1
    with pytest.raises(ValueError, match="keyPosition"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"keyPosition": 0,', b'"keyPosition": "0",', 1))])


def test_duplicate_time_period_ids_raise():
    """Copy the whole 2026-03 TIME_PERIOD value entry onto 2026-02 (id AND start/end stay
    consistent): two indices then decode to the same period - a duplicate, never a merge."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"id": "2026-03"') == 1
    t = b.replace(b'"id": "2026-03"', b'"id": "2026-02"', 1)
    t = t.replace(b'"start": "2026-03-01T00:00:00"', b'"start": "2026-02-01T00:00:00"', 1)
    t = t.replace(b'"end": "2026-03-31T23:59:59"', b'"end": "2026-02-28T23:59:59"', 1)
    t = t.replace(b'"name": "2026-03"', b'"name": "2026-02"', 1)
    t = t.replace(b'"en-US": "2026-03"', b'"en-US": "2026-02"', 1)
    with pytest.raises(ValueError, match="duplicate"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=t)])


def test_malformed_time_period_id_raises():
    b = body(FILE_OF["oecd.cli.PT"])
    with pytest.raises(ValueError, match="TIME_PERIOD"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"id": "2026-03"', b'"id": "2026.03"', 1))])


def test_extra_series_key_in_dataset_raises():
    """One requested series -> exactly one series entry; an extra (here out-of-range) series
    identity is a format/identity anomaly, never silently dropped."""
    b = body(FILE_OF["oecd.cli.PT"])
    assert b.count(b'"0:0:0:0:0:0:0:0:0"') == 1
    with pytest.raises(ValueError, match="series|index|out of range"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", body_=b.replace(
            b'"0:0:0:0:0:0:0:0:0"', b'"0:0:0:0:0:0:0:0:1"', 1))])


def test_url_body_identity_mismatch_raises():
    """The response URL declares the series identity; pairing the CLI request URL with the
    employment payload is drift, not a parse."""
    with pytest.raises(ValueError, match="identity|pin|drift"):
        _parse(["oecd.cli.PT", "oecd.employment.PT"],
               [_resp("oecd.cli.PT", body_=body(FILE_OF["oecd.employment.PT"])),
                _resp("oecd.employment.PT")])


def test_unrequested_series_response_raises():
    with pytest.raises(ValueError, match="unrequested"):
        _parse(["oecd.cli.PT"], [_resp("oecd.unemp_m.PT")])


def test_same_series_archived_twice_raises():
    with pytest.raises(ValueError, match="twice|duplicate"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT"), _resp("oecd.cli.PT")])


def test_url_query_duplicate_key_raises():
    u = (f"{API_BASE}/data/{NC['oecd.cli.PT']}"
         "?startPeriod=2025-10&startPeriod=2025-11")
    with pytest.raises(ValueError, match="duplicate"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", url=u,
                                       params={"startPeriod": "2025-10"})])


def test_url_query_unknown_key_raises():
    u = f"{API_BASE}/data/{NC['oecd.cli.PT']}?startPeriod=2025-10&detail=full"
    with pytest.raises(ValueError, match="unreviewed|unknown"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", url=u,
                                       params={"startPeriod": "2025-10"})])


def test_url_query_must_not_contradict_archived_params():
    u = f"{API_BASE}/data/{NC['oecd.cli.PT']}?startPeriod=2025-11"
    with pytest.raises(ValueError, match="disagree|mismatch"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", url=u,
                                       params={"startPeriod": "2025-10"})])


def test_archived_params_unknown_key_raises():
    with pytest.raises(ValueError, match="params"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT",
                                       params={"startPeriod": "2025-10", "fo": "1"})])


def test_archived_params_must_be_canonical_period_literals():
    for p in ("2025-1", "2025/10", "202513", "2025-13"):
        with pytest.raises(ValueError, match="param"):
            _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", params={"startPeriod": p})])


def test_archived_window_is_a_containment_constraint_on_the_payload():
    """A response archived with a declared window must not decode rows OUTSIDE it: a truncated
    or rebound window can never promote the same bytes to a different archive."""
    with pytest.raises(ValueError, match="window|extent|outside"):
        _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", params={"startPeriod": "2026-06"})])
    with pytest.raises(ValueError, match="window|extent|outside"):
        _parse(["oecd.cli.PT"], [_resp(
            "oecd.cli.PT", params={"startPeriod": "2025-10", "endPeriod": "2026-05"})])


def test_full_history_archive_without_params_parses():
    """The archived-window check binds only when a window was declared; a fixture replayed with
    an empty-params identity is complete by itself."""
    parsed = _parse(["oecd.cli.PT"], [_resp("oecd.cli.PT", params={})])
    assert len(parsed["oecd.cli.PT"]) == 13


def test_duplicate_native_code_specs_rejected():
    s = registry_specs()["oecd.cli.PT"]
    twin = s.model_copy(update={"id": "oecd.cli.PT_twin"})
    with pytest.raises(ValueError, match="duplicate native_code"):
        OecdSource().parse([s, twin], [_resp("oecd.cli.PT")])


def test_validate_roundtrip_on_all_six_fixtures():
    specs = specs_of(ALL_SIX)
    parsed = _parse(ALL_SIX, _six_responses())
    by_id = {s.id: s for s in specs}
    for sid, rows in parsed.items():
        obs, rej = validate(by_id[sid], rows)
        assert not rej, (sid, rej[:3])
        assert {o.status_flag for o in obs} == {"normal"}
        assert {o.period for o in obs} == set(EXPECTED[sid])
        assert all(o.value_text == EXPECTED[sid][o.period] for o in obs)


def test_fetch_full_history_default_requests_each_series_once_with_sdmx_json_accept_header():
    http = FixtureHttp()
    out = list(OecdSource().fetch(specs_of(ALL_SIX), http))
    assert [c[0] for c in http.calls] == sorted(NC.values())  # sorted native_code order
    assert all(c[1] == {} for c in http.calls)  # NO window params: full history by default
    assert all(c[2] == {"Accept": "application/vnd.sdmx.data+json;version=2.0"}
               for c in http.calls)
    assert len(out) == 6 and all(r.status == 200 and r.params == {} for r in out)
    assert all(r.url == f"{API_BASE}/data/{r.url.split('/data/')[1]}" for r in out)  # no query
    for r in out:
        import json as _json
        assert _json.loads(r.body)  # genuine archived bodies came back


def test_fetch_bounded_window_sends_exact_period_params_and_final_urls_match_evidence():
    http = FixtureHttp()
    out = list(OecdSource(start_period="2025-10").fetch(specs_of(ALL_SIX), http))
    assert all(c[1] == {"startPeriod": "2025-10"} for c in http.calls)
    # every yielded final URL byte-equals the archived evidence URL of its series
    by_file = {e["file"]: e for e in MANIFEST["files"]}
    for r in out:
        nc = r.url.split("/data/")[1].split("?")[0]
        assert r.url == by_file[JSON_BY_NATIVE_CODE[nc]]["url"]
        assert r.params == {"startPeriod": "2025-10"}
    http = FixtureHttp()
    list(OecdSource(start_period="2020-01", end_period="2026-12").fetch(
        specs_of(["oecd.cli.PT"]), http))
    assert http.calls[0][1] == {"startPeriod": "2020-01", "endPeriod": "2026-12"}


def test_fetch_rejects_malformed_window_literals_at_construction():
    for p in ("2025-1", "2025/01", "jan-2025", "2025-13", "２０２５-10"):
        with pytest.raises(ValueError, match="period"):
            OecdSource(start_period=p)
    with pytest.raises(ValueError, match="period"):
        OecdSource(end_period="2026-99")
    with pytest.raises(ValueError, match="window|period"):
        OecdSource(start_period="2026-10", end_period="2025-10")  # inverted window


def test_fetch_yields_non2xx_for_the_pipeline_to_classify_without_retry_or_filter():
    nc = NC["oecd.cli.PT"]
    http = FixtureHttp(status={nc: 404})
    out = list(OecdSource().fetch(specs_of(["oecd.cli.PT"]), http))
    assert [r.status for r in out] == [404] and len(http.calls) == 1


def test_pipeline_run_on_fixtures_writes_and_links_provenance(tmp_path):
    specs = specs_of(ALL_SIX)
    db = open_db(tmp_path / "t.db")
    try:
        sync_registry(db, specs)
        r = run_dataset(db, RawStore(tmp_path / "raw"),
                        OecdSource(start_period="2025-10"), specs, FixtureHttp())
        assert r.state == "pending-verification"
        assert r.n_written == 77 and r.n_quarantined == 0
        rows = db.conn.execute(
            "SELECT series_id, COUNT(*), MIN(period), MAX(period) FROM observation "
            "GROUP BY series_id ORDER BY series_id").fetchall()
        assert [(sid, n, lo, hi) for sid, n, lo, hi in rows] == [
            (sid, len(EXPECTED[sid]), min(EXPECTED[sid]), max(EXPECTED[sid]))
            for sid in sorted(ALL_SIX)]
        assert db.conn.execute("SELECT COUNT(*) FROM raw_fetch WHERE ok=1").fetchone()[0] == 6
        assert {x[0] for x in db.conn.execute(
            "SELECT DISTINCT raw_fetch_id FROM observation").fetchall()} == {1, 2, 3, 4, 5, 6}
    finally:
        db.close()


def test_registry_native_codes_complete_and_unique():
    reg = registry_specs()
    assert set(reg) == set(ALL_SIX)
    for sid, s in reg.items():
        agency, dataflow, key = parse_native_code(s.native_code)  # raises unless canonical
        assert s.native_code == NC[sid]
        assert len(key.split(".")) == 9
        assert s.url == f"{API_BASE}/data/{s.native_code}"
        assert s.active is True
    codes = [s.native_code for s in reg.values()]
    assert len(set(codes)) == 6


def test_fixture_manifest_sha256_pins():
    import hashlib
    assert len(MANIFEST["files"]) == 6
    for e in MANIFEST["files"]:
        blob = (FIX / e["file"]).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == e["sha256"], e["file"]
        assert len(blob) == e["bytes"] and 0 < e["bytes"] <= 200 * 1024
        assert e["status"] == 200
        assert e["url"].startswith(f"{API_BASE}/data/") and "startPeriod=2025-10" in e["url"]
