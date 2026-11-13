"""Banco de Portugal (BPstat) source adapter tests — real recorded JSON-stat fixtures
(tests/ingest/fixtures/bportugal/, 2026-11-11). Named expectations were cross-checked against
the portal's own /api/observations/ channel (see fixtures/bportugal/verify/MANIFEST.json).
"""
import json

import pytest

from ingest.db import open_db
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.sources import RawResponse
from ingest.sources.bportugal import BPortugalSource, parse_native_code
from ingest.validate import validate
from tests.ingest.bportugal_fixtures import (
    MANIFEST,
    SETS,
    FixtureHttp,
    all_specs,
    body,
    registry_specs,
    specs_of,
)

# Named cells: (series id, period, publisher token) — every row cross-checked against the
# portal channel /api/observations/ recorded reply (fixtures/bportugal/verify/).
EXPECTED = {
    ("bportugal.euribor_1m.EA", "1994-01"): ("7.1200", "normal"),
    ("bportugal.euribor_3m.EA", "1994-01"): ("6.9100", "normal"),
    ("bportugal.euribor_6m.EA", "1994-01"): ("6.6700", "normal"),
    ("bportugal.euribor_12m.EA", "1994-01"): ("6.3400", "normal"),
    ("bportugal.euribor_1m.EA", "2026-10"): ("2.4358", "normal"),
    ("bportugal.euribor_12m.EA", "2020-04"): ("-0.1082", "normal"),  # negative-rate era
    ("bportugal.pt_10y.PT", "1993-07"): ("10.67", "normal"),
    ("bportugal.pt_10y.PT", "2023-08"): ("3.31", "normal"),  # revised cell (was 3.30 first pub.)
    ("bportugal.pt_10y.PT", "2026-10"): ("3.92", "normal"),
    ("bportugal.de_10y.DE", "2026-10"): ("3.43", "normal"),
    ("bportugal.credit_housing.PT", "1999-12"): ("42179.6", "normal"),
    ("bportugal.credit_housing.PT", "2026-09"): ("120179.0", "normal"),
    ("bportugal.credit_consumer.PT", "1999-12"): ("6770.1", "normal"),
    ("bportugal.credit_consumer.PT", "2026-09"): ("22766.1", "normal"),
    ("bportugal.deposits_households.PT", "1999-12"): ("77865.3", "normal"),
    ("bportugal.deposits_households.PT", "2026-09"): ("203204.0", "normal"),
    ("bportugal.eur_usd.EA", "2000-10"): ("0.8552", "normal"),
    ("bportugal.eur_usd.EA", "2026-10"): ("1.1202", "normal"),
}


def parse_all():
    specs = all_specs()
    order = ["credit", "deposits", "euribor", "yields", "eurusd"]  # group order, as in fetch
    return BPortugalSource().parse(
        specs, [RawResponse(url=(m := MANIFEST["sets"][name])["url"], params=m["params"],
                            status=200, body=body(m["file"]))
                for name in order]), specs


def test_parse_fixture_yields_expected_rows():
    parsed, _ = parse_all()
    found = {(sid, p): (r.value_raw, r.flag_raw)
             for sid, rows in parsed.items() for r in rows
             for p in [r.period_raw] if (sid, p) in EXPECTED}
    assert found == EXPECTED
    # every series present with its full history:
    sizes = {sid: len(rows) for sid, rows in parsed.items()}
    assert sizes == {
        "bportugal.euribor_1m.EA": 394, "bportugal.euribor_3m.EA": 394,
        "bportugal.euribor_6m.EA": 394, "bportugal.euribor_12m.EA": 394,
        "bportugal.pt_10y.PT": 400, "bportugal.de_10y.DE": 400,  # 78 value-None rows included
        "bportugal.credit_housing.PT": 562, "bportugal.credit_consumer.PT": 562,
        "bportugal.deposits_households.PT": 562, "bportugal.eur_usd.EA": 334}


def test_no_value_cells_become_value_none_rows():
    parsed, _ = parse_all()
    de = parsed["bportugal.de_10y.DE"]
    no_value = [r for r in de if r.value_raw is None]
    assert len(no_value) == 78  # DE yields start 2000-01; 1993-07..1999-12 are empty cells
    assert all(r.flag_raw is None for r in no_value)
    assert de[0].period_raw == "1993-07" and de[78].period_raw == "2000-01"


def test_tokens_are_publisher_strings_never_floats():
    parsed, _ = parse_all()
    rows = [r for rows in parsed.values() for r in rows]
    assert all(r.value_raw is None or type(r.value_raw) is str for r in rows)
    assert all(r.period_raw is None or type(r.period_raw) is str for r in rows)
    one = next(r for r in parsed["bportugal.euribor_1m.EA"] if r.period_raw == "1994-01")
    assert one.value_raw == "7.1200"  # trailing zeros of the publisher's fixed-decimal rendering


def test_parse_preserves_status_flags():
    parsed, _ = parse_all()
    flags = {r.flag_raw for rows in parsed.values() for r in rows}
    assert flags == {"normal", None}  # observed vocabulary: every valued cell is 'F' = final


def test_tampered_status_token_raises():
    tampered = body("yields.json").replace(b'"status":["F"', b'"status":["P"', 1)
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="status"):
        BPortugalSource().parse(specs, [RawResponse(url=MANIFEST["sets"]["yields"]["url"],
                                                    params={}, status=200, body=tampered)])


def test_valued_cell_without_status_raises():
    tampered = body("yields.json").replace(b'"status":["F"', b'"status":[null', 1)
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="status"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=tampered)])


def test_status_code_on_a_valueless_cell_raises():
    # 12099464's pt block is fully valued; give its first cell status 'F' but remove the value
    tampered = body("yields.json").replace(b'"value":["10.67"', b'"value":[null', 1)
    assert b'"status":["F"' in tampered  # the cell keeps its F
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="status"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=tampered)])


def test_parse_html_error_page_raises():
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="markup|HTML"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=body("error_html_spa_page.html"))])


def test_parse_api_error_body_raises():
    specs = specs_of("yields")
    with pytest.raises(ValueError):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=400,
                                                    body=body("error_bad_series_ids.json"))])


def test_parse_rejects_bad_json():
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="JSON"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=b'{"broken":')])


def test_truncated_payload_raises():
    doc = json.loads(body("yields.json"))
    doc["value"] = doc["value"][:-7]
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="truncated|length|cells"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=json.dumps(doc).encode())])


def test_duplicate_period_labels_raise():
    tampered = body("credit.json").replace(b'"1997-02-28","1997-03-31"',
                                           b'"1997-02-28","1997-02-28"', 1)
    specs = specs_of("credit")
    with pytest.raises(ValueError, match="duplicate"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=tampered)])


def test_wrong_series_id_in_response_raises():
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="series"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=body("euribor.json"))])


def test_wrong_unit_label_raises():
    tampered = body("yields.json").replace(b'"label":{"3327":"Percentage"}',
                                           b'"label":{"3327":"Euro"}', 1)
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="unit"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=tampered)])


def test_wrong_periodicity_label_raises():
    tampered = body("yields.json").replace(b'"label":{"4264":"Monthly"}',
                                           b'"label":{"4264":"Quarterly"}', 1)
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="[Pp]eriodicity|frequenc"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=tampered)])


def test_spec_frequency_mismatch_raises():
    specs = [s.model_copy(update={"frequency": "D"}) for s in specs_of("yields")]
    with pytest.raises(ValueError, match="[Pp]eriodicity|frequenc"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=body("yields.json"))])


def test_wrong_territory_raises():
    tampered = body("yields.json").replace(b'"label":{"126":"Germany","349":"Portugal"}',
                                           b'"label":{"126":"Portugal","349":"Germany"}', 1)
    specs = specs_of("yields")
    with pytest.raises(ValueError, match="territor|geograph"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=tampered)])


def test_double_mapped_series_raise():
    """Two requested series whose category pins collapse onto the same cell block."""
    doc = json.loads(body("yields.json"))
    pt = next(s for s in doc["extension"]["series"] if s["id"] == 12099464)
    doc["extension"]["series"].append({**pt, "id": 12099465})  # valid id shape, same pins
    pt_spec = next(s for s in specs_of("yields") if s.id == "bportugal.pt_10y.PT")
    fake = pt_spec.model_copy(update={"id": "bportugal.pt_10y_dup.PT",
                                      "native_code": "12099465:26/690b7b36fd36c0dbe249c48cbbc39524"})
    with pytest.raises(ValueError, match="identical|double|same"):
        BPortugalSource().parse([pt_spec, fake], [RawResponse(url="", params={}, status=200,
                                                              body=json.dumps(doc).encode())])


def test_unknown_requested_series_raises():
    doc = json.loads(body("yields.json"))  # carries 12099464 + 12560098 only
    specs = specs_of("euribor")  # asks for euribor ids
    with pytest.raises(ValueError, match="series"):
        BPortugalSource().parse(specs, [RawResponse(url="", params={}, status=200,
                                                    body=json.dumps(doc).encode())])


def test_response_index_points_at_the_request_of_each_row():
    specs = [s for name in SETS for s in specs_of(name)]
    responses = [RawResponse(url=MANIFEST["sets"][n]["url"], params={}, status=200,
                             body=body(MANIFEST["sets"][n]["file"])) for n in GROUP_ORDER]
    parsed = BPortugalSource().parse(specs, responses)
    for group_index, name in enumerate(GROUP_ORDER):
        for r in next(rws for sid, rws in parsed.items()
                      if sid == f"bportugal.{_LEAD[name]}")[:3]:
            assert r.response_index == group_index


# deterministic dataset-group order of BPortugalSource: ascending (domain, dataset)
GROUP_ORDER = ["credit", "deposits", "euribor", "yields", "eurusd"]
_LEAD = {"euribor": "euribor_1m.EA", "yields": "pt_10y.PT", "credit": "credit_housing.PT",
         "deposits": "deposits_households.PT", "eurusd": "eur_usd.EA"}


def test_fetch_asks_each_dataset_once_with_decimal_and_sorted_ids():
    specs = [s for name in SETS for s in specs_of(name)]
    http = FixtureHttp()
    out = list(BPortugalSource().fetch(specs, http))
    assert http.calls == GROUP_ORDER  # one request per dataset, in (domain, dataset) order
    assert [r.status for r in out] == [200] * 5
    for name in SETS:
        m = MANIFEST["sets"][name]
        assert m["params"]["decimal"] == "true" and m["params"]["lang"] == "EN"
        assert m["params"]["series_ids"] == ",".join(sorted(m["series_ids"]))


def test_fetch_without_configured_timeout_keeps_legacy_signature():
    """bportugal registry has no timeout_s: get() must be called WITHOUT the timeout kwarg,
    so older Http doubles (3-parameter get) keep working — the INE pattern."""
    from ingest.http import HttpResult

    class ThreeParamDouble:
        def __init__(self):
            self.urls = []

        def get(self, url, params=None, headers=None):  # no timeout parameter at all
            self.urls.append(url)
            m = MANIFEST["sets"]["yields"]
            return HttpResult(status=200, body=body(m["file"]), url=m["url"])

    http = ThreeParamDouble()
    out = list(BPortugalSource().fetch(specs_of("yields"), http))
    base = MANIFEST["sets"]["yields"]["url"].split("?")[0]
    assert len(out) == 1 and http.urls == [base]


def test_de_first_value_cell_is_552():
    parsed, _ = parse_all()
    de = parsed["bportugal.de_10y.DE"]
    assert de[78].period_raw == "2000-01" and de[78].value_raw == "5.52"


def test_parse_native_code():
    assert parse_native_code("12099464:26/690b7b36fd36c0dbe249c48cbbc39524") == \
        (12099464, 26, "690b7b36fd36c0dbe249c48cbbc39524")


# --- sparse JSON-stat cell columns (value/status as dicts) ----------------------------------

def _sparse(doc: dict) -> dict:
    """Payload -> the equivalent JSON-stat sparse-dict form: non-null cells only, keyed by the
    canonical flat index."""
    out = dict(doc)
    for key in ("value", "status"):
        if isinstance(doc.get(key), list):
            out[key] = {str(i): v for i, v in enumerate(doc[key]) if v is not None}
    return out


def _parse_payload(raw: bytes):
    return BPortugalSource().parse(specs_of("yields"),
                                   [RawResponse(url="", params={}, status=200, body=raw)])


def test_sparse_form_parses_identically_to_dense():
    """Dense list and canonical sparse dict are two spellings of the same cells; parse results
    must be identical (values AND statuses, the 78 DE value-None cells included)."""
    dense = body("yields.json")
    sparse_body = json.dumps(_sparse(json.loads(dense))).encode()
    assert _parse_payload(sparse_body) == _parse_payload(dense)


def _alias_payload(alias: str) -> bytes:
    doc = _sparse(json.loads(body("yields.json")))
    doc["value"][alias] = "9.99"  # collides with a canonical cell if int() folding is accepted
    return json.dumps(doc).encode()


@pytest.mark.parametrize("alias", ["00", "01", "+1", " 1", "٣", "1_0"])
def test_sparse_noncanonical_alias_keys_raise(alias):
    """'00' and '0' address the SAME cell: accepting both silently overwrites data (review
    finding, 2026-11-11: _cells_column({'0': '1.10', '00': '2.20'}, ...) kept only '2.20').
    Only the canonical ASCII decimal spelling of a flat index is legal — no leading zeros,
    signs, whitespace, Unicode digit aliases or other int() foldings."""
    with pytest.raises(ValueError, match="sparse value key"):
        _parse_payload(_alias_payload(alias))


def test_sparse_out_of_bounds_key_still_raises():
    doc = _sparse(json.loads(body("yields.json")))
    doc["value"][str(len(json.loads(body("yields.json"))["value"]))] = "9.99"  # past the end
    with pytest.raises(ValueError, match="outside"):
        _parse_payload(json.dumps(doc).encode())


def test_sparse_alias_payload_fails_validation_before_any_row_is_written(tmp_path):
    """Through the pipeline: the aliased payload is a failed-validation (format_change), zero
    observations and zero quarantine rows committed."""
    specs = all_specs()
    db = open_db(tmp_path / "t.db")
    try:
        from ingest.registry import sync_registry
        sync_registry(db, specs)
        r = run_dataset(db, RawStore(tmp_path / "raw"), BPortugalSource(), specs,
                        FixtureHttp({"yields": _alias_payload("00")}))
        assert r.state == "failed-validation" and r.n_written == 0 and r.n_quarantined == 0
        assert db.conn.execute("SELECT COUNT(*) FROM observation").fetchone()[0] == 0
        assert db.conn.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0] == 0
    finally:
        db.close()


@pytest.mark.parametrize("code", [None, "", "12099464", "12099464:",
                                  "12099464/690b7b36fd36c0dbe249c48cbbc39524",
                                  "abc:26/690b7b36fd36c0dbe249c48cbbc39524",
                                  "12099464:xy/690b7b36fd36c0dbe249c48cbbc39524",
                                  "12099464:26/nothex",
                                  "12099464:26/690B7b36fd36c0dbe249c48cbbc39524",
                                  "126068439:22/2829cb9155cb4f6ba6906db6b204c4bc:extra"])
def test_parse_native_code_rejects_malformed(code):
    with pytest.raises(ValueError):
        parse_native_code(code)


def test_registry_native_codes_complete_and_active_covered_by_fixtures():
    reg = registry_specs()
    assert len(reg) == 10
    covered = {sid for m in MANIFEST["sets"].values() for sid in m["series_ids"]}
    for spec in reg.values():
        sid, _, _ = parse_native_code(spec.native_code)
        assert str(sid) in covered, spec.id  # every registry series has a recorded fixture


def test_active_native_codes_are_unique():
    codes = [s.native_code for s in registry_specs().values() if s.active]
    assert len(codes) == len(set(codes))


def test_pipeline_run_on_fixtures_writes_and_quarantines(tmp_path):
    specs = all_specs()
    db = open_db(tmp_path / "t.db")
    try:
        from ingest.registry import sync_registry
        sync_registry(db, specs)
        r = run_dataset(db, RawStore(tmp_path / "raw"), BPortugalSource(), specs, FixtureHttp())
        assert r.state == "pending-verification"
        assert r.n_written == 1576 + 722 + 1124 + 562 + 334  # valued cells
        assert r.n_quarantined == 78  # DE yield empty cells 1993-07..1999-12
        reasons = db.conn.execute("SELECT DISTINCT reason FROM quarantine").fetchall()
        assert [x[0] for x in reasons] == ["non_numeric"]
    finally:
        db.close()


def test_validate_roundtrip_units_and_flags():
    parsed, specs = parse_all()
    by_id = {s.id: s for s in specs}
    for sid, rows in parsed.items():
        obs, rej = validate(by_id[sid], rows)
        assert not rej or sid == "bportugal.de_10y.DE"
        assert {o.status_flag for o in obs} == {"normal"}


def test_bportugal_has_an_independent_channel_and_a_verifier():
    import importlib
    src = next(iter(registry_specs().values())).source
    assert src.verifiable is True
    assert importlib.import_module("ingest.verifiers.bportugal") is not None
