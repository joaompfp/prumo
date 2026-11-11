"""REN DataHub source adapter tests — real recorded servicebus JSON fixtures
(tests/ingest/fixtures/ren/, 2026-11-11; bytes sha256-verified copies of the Task 12 discovery
archive). Pinned tokens were cross-checked live against the independent portal CSV export
(verify/ set and fixtures/ren/MANIFEST.json)."""
import json
from datetime import date

import pytest

from ingest.db import open_db
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources import RawResponse
from ingest.sources.ren import (
    API_BASE,
    BALANCE_ENDPOINT,
    PRICES_ENDPOINT,
    RenSource,
    completed_months,
    parse_native_code,
)
from ingest.validate import validate
from tests.ingest.ren_fixtures import (
    MANIFEST,
    FixtureHttp,
    all_specs,
    balance_specs,
    body,
    registry_specs,
    response_of,
)

# Pinned (series id, period) -> publisher token, read from the archived bytes of
# balance_2026-09 / balance_2010-01 / prices_2026-09 (byte sha256 in MANIFEST.json).
EXPECTED_2026_09 = {
    "ren.electricity_consumption.PT": "4442",
    "ren.electricity_production_total.PT": "3360",
    "ren.electricity_production_renewable.PT": "2327",
    "ren.electricity_production_non_renewable.PT": "599",
    "ren.electricity_hydro.PT": "645",
    "ren.electricity_wind.PT": "727",
    "ren.electricity_solar.PT": "725",
    "ren.electricity_biomass.PT": "230",
    "ren.electricity_natural_gas.PT": "579",
    "ren.electricity_natural_gas_ccgt.PT": "510",
    "ren.electricity_imports.PT": "1697",
    "ren.electricity_exports.PT": "87",
    "ren.electricity_net_imports.PT": "1616",
    "ren.electricity_price_mibel.PT": "143.9",
}
EXPECTED_2010_01 = {
    "ren.electricity_consumption.PT": "4920",
    "ren.electricity_production_total.PT": "5206",
    "ren.electricity_production_renewable.PT": "3663",
    "ren.electricity_production_non_renewable.PT": "1496",
    "ren.electricity_hydro.PT": "2526",
    "ren.electricity_wind.PT": "975",
    "ren.electricity_solar.PT": "8",
    "ren.electricity_biomass.PT": "154",
    "ren.electricity_natural_gas.PT": "885",
    "ren.electricity_natural_gas_ccgt.PT": "567",
    "ren.electricity_imports.PT": "116",
    "ren.electricity_exports.PT": "380",
    "ren.electricity_net_imports.PT": "-263",
}


def _raw(set_name: str) -> RawResponse:
    url, params, status, doc = response_of(set_name)
    return RawResponse(url=url, params=params, status=status, body=doc)


def test_parse_fixture_yields_expected_rows():
    parsed = RenSource(periods=("2026-09",)).parse(
        all_specs(), [_raw("balance_2026-09"), _raw("prices_2026-09")])
    got = {sid: rows[0] for sid, rows in parsed.items()}
    for sid, token in EXPECTED_2026_09.items():
        assert (got[sid].period_raw, got[sid].value_raw) == ("2026-09", token)
    assert all(len(rows) == 1 for rows in parsed.values())


def test_parse_2010_month_yields_expected_rows():
    parsed = RenSource(periods=("2010-01",)).parse(balance_specs(), [_raw("balance_2010-01")])
    for sid, token in EXPECTED_2010_01.items():
        row = parsed[sid][0]
        assert (row.period_raw, row.value_raw) == ("2010-01", token)


def test_retired_and_unmapped_types_are_skipped_not_rejected():
    """2010-01 carries CARVAO (retired coal) and other types the registry does not select:
    skipping them is correct; rejecting them would break valid history."""
    parsed = RenSource(periods=("2010-01",)).parse(balance_specs(), [_raw("balance_2010-01")])
    assert len(parsed) == 13 and all(len(rows) == 1 for rows in parsed.values())
    # sanity: the unmapped tokens really are in the payload
    assert b'"CARVAO"' in body("balance_2010-01.json")


def test_tokens_are_publisher_strings_never_floats():
    parsed = RenSource(periods=("2026-09",)).parse(
        all_specs(), [_raw("balance_2026-09"), _raw("prices_2026-09")])
    rows = [r for rows in parsed.values() for r in rows]
    assert all(type(r.value_raw) is str and type(r.period_raw) is str for r in rows)
    assert parsed["ren.electricity_price_mibel.PT"][0].value_raw == "143.9"  # not 143.90000001
    parsed_old = RenSource(periods=("2010-01",)).parse(balance_specs(), [_raw("balance_2010-01")])
    assert parsed_old["ren.electricity_net_imports.PT"][0].value_raw == "-263"  # negative token


def test_every_row_flag_is_normal_no_publisher_flag_surface():
    """Neither REN endpoint exposes an observation status surface (archived bytes): every stored
    row is explicitly 'normal' by declaration."""
    parsed = RenSource(periods=("2026-09",)).parse(
        all_specs(), [_raw("balance_2026-09"), _raw("prices_2026-09")])
    assert {r.flag_raw for rows in parsed.values() for r in rows} == {"normal"}
    assert {r.unit_raw for rows in parsed.values() for r in rows} == {None}  # no unit surface


def test_response_index_points_at_each_rows_response():
    parsed = RenSource(periods=("2010-01", "2026-09")).parse(
        balance_specs(), [_raw("balance_2010-01"), _raw("balance_2026-09")])
    for rows in parsed.values():
        assert [r.response_index for r in rows] == [0, 1]
        assert [r.period_raw for r in rows] == ["2010-01", "2026-09"]


def test_parse_html_error_page_raises():
    with pytest.raises(ValueError, match="markup|HTML"):
        RenSource(periods=("2026-09",)).parse(
            all_specs(), [RawResponse(url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                                      params={"culture": "pt-PT", "year": "2026", "month": "09"},
                                      body=b"<!DOCTYPE html><html></html>")])


def test_parse_rejects_bad_json():
    with pytest.raises(ValueError, match="JSON"):
        RenSource(periods=("2026-09",)).parse(
            balance_specs(), [RawResponse(url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                                          params={"culture": "pt-PT", "year": "2026",
                                                  "month": "09"}, body=b'{"broken":')])


def test_parse_rejects_duplicate_json_keys():
    with pytest.raises(ValueError, match="duplicate"):
        RenSource(periods=("2026-09",)).parse(
            balance_specs(), [RawResponse(
                url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                params={"culture": "pt-PT", "year": "2026", "month": "09"},
                body=b'[{"monthly_Accumulation":5,"type":"CONSUMO","type":"X"},...]')])


def test_parse_rejects_non_2xx_responses():
    with pytest.raises(ValueError, match="HTTP 404"):
        RenSource(periods=("2026-11",)).parse(balance_specs(), [_raw("error_404_unpublished_month")])


def test_missing_selected_type_raises():
    doc = json.loads(body("balance_2026-09.json"))
    doc = [e for e in doc if e["type"] != "CONSUMO"]
    with pytest.raises(ValueError, match="CONSUMO"):
        RenSource(periods=("2026-09",)).parse(
            balance_specs(), [RawResponse(url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                                          params={"culture": "pt-PT", "year": "2026",
                                                  "month": "09"}, body=json.dumps(doc).encode())])


def test_duplicate_type_in_payload_raises():
    doc = json.loads(body("balance_2026-09.json"))
    doc.append({"monthly_Accumulation": 1, "type": "CONSUMO"})
    with pytest.raises(ValueError, match="repeat|duplicate"):
        RenSource(periods=("2026-09",)).parse(
            balance_specs(), [RawResponse(url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                                          params={"culture": "pt-PT", "year": "2026",
                                                  "month": "09"}, body=json.dumps(doc).encode())])


def test_entry_with_missing_field_raises():
    doc = json.loads(body("balance_2026-09.json"))
    del doc[0]["monthly_Accumulation"]
    with pytest.raises(ValueError, match="monthly_Accumulation"):
        RenSource(periods=("2026-09",)).parse(
            balance_specs(), [RawResponse(url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                                          params={"culture": "pt-PT", "year": "2026",
                                                  "month": "09"}, body=json.dumps(doc).encode())])


def test_entry_with_unexpected_status_field_raises():
    """A new status-like field is an unreviewed surface: fail closed, never guess the flag."""
    doc = json.loads(body("balance_2026-09.json"))
    doc[0]["status"] = "F"
    with pytest.raises(ValueError):
        RenSource(periods=("2026-09",)).parse(
            balance_specs(), [RawResponse(url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                                          params={"culture": "pt-PT", "year": "2026",
                                                  "month": "09"}, body=json.dumps(doc).encode())])


def test_non_numeric_value_token_raises():
    doc = json.loads(body("balance_2026-09.json"))
    doc[0]["monthly_Accumulation"] = "abc"
    with pytest.raises(ValueError, match="token"):
        RenSource(periods=("2026-09",)).parse(
            balance_specs(), [RawResponse(url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                                          params={"culture": "pt-PT", "year": "2026",
                                                  "month": "09"}, body=json.dumps(doc).encode())])


def _tampered_balance(tampered: bytes) -> RawResponse:
    return RawResponse(url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                       params={"culture": "pt-PT", "year": "2026", "month": "09"},
                       body=tampered)


def test_quoted_number_token_raises_even_when_numeric_shaped():
    """A JSON string is NOT a publisher number, even with valid token grammar: with the
    primitive type erased by the number loader, '"04442"' would parse as the token '04442' — stored
    verbatim as the publisher's number AND still Decimal-verifying against the CSV channel
    (04442 == 4442), a silent type flip neither layer detects. The payload must fail closed."""
    tampered = body("balance_2026-09.json").replace(
        b'{"monthly_Accumulation":4442,"type":"CONSUMO"}',
        b'{"monthly_Accumulation":"04442","type":"CONSUMO"}', 1)
    with pytest.raises(ValueError, match="number token"):
        RenSource(periods=("2026-09",)).parse(balance_specs(), [_tampered_balance(tampered)])


def test_numeric_type_label_raises():
    """The balance 'type' label must be a genuine JSON string: a JSON number is not a label
    (type confusion must fail closed, not slip through a number-as-string loader). Tampered on
    an UNMAPPED row so no other guard (missing selected type) can trip first."""
    tampered = body("balance_2026-09.json").replace(
        b'{"monthly_Accumulation":535,"type":"CONSUMO_ARMAZENAMENTO"}',
        b'{"monthly_Accumulation":535,"type":535}', 1)
    with pytest.raises(ValueError, match="type"):
        RenSource(periods=("2026-09",)).parse(balance_specs(), [_tampered_balance(tampered)])


def test_price_quoted_token_raises():
    """Every price surface (PT/ES metrics, capacity, scalars) routes through the same number
    gate: a QUOTED 'Preço Médio' is a format change, not a token."""
    tampered = body("prices_2026-09.json").replace(
        b'"Pre\xc3\xa7o M\xc3\xa9dio":143.9', b'"Pre\xc3\xa7o M\xc3\xa9dio":"143.9"', 1)
    with pytest.raises(ValueError, match="number token"):
        RenSource(periods=("2026-09",)).parse(
            [s for s in all_specs() if (s.native_code or "").startswith(PRICES_ENDPOINT)],
            [RawResponse(url=f"{API_BASE}/{PRICES_ENDPOINT}", status=200,
                         params={"culture": "pt-PT", "year": "2026", "month": "09"},
                         body=tampered)])


def test_price_month_key_must_match_the_requested_month():
    tampered = body("prices_2026-09.json").replace('"setembro"'.encode(), '"agosto"'.encode(), 1)
    with pytest.raises(ValueError, match="month key"):
        RenSource(periods=("2026-09",)).parse(
            [s for s in all_specs() if (s.native_code or "").startswith(PRICES_ENDPOINT)],
            [RawResponse(url=f"{API_BASE}/{PRICES_ENDPOINT}", status=200,
                         params={"culture": "pt-PT", "year": "2026", "month": "09"},
                         body=tampered)])


def test_price_block_unknown_surface_raises():
    tampered = body("prices_2026-09.json").replace(
        '"Capacidade [MW]"'.encode(), '"Outro Bloco"'.encode(), 1)
    with pytest.raises(ValueError, match="unreviewed"):
        RenSource(periods=("2026-09",)).parse(
            [s for s in all_specs() if (s.native_code or "").startswith(PRICES_ENDPOINT)],
            [RawResponse(url=f"{API_BASE}/{PRICES_ENDPOINT}", status=200,
                         params={"culture": "pt-PT", "year": "2026", "month": "09"},
                         body=tampered)])


def test_request_without_explicit_year_month_raises():
    """The period identity of a balance response is its request: without params we refuse to
    guess (the API silently serves a wrong-vintage answer when dates are omitted)."""
    with pytest.raises(ValueError, match="params"):
        RenSource(periods=("2026-09",)).parse(
            balance_specs(), [RawResponse(url=f"{API_BASE}/{BALANCE_ENDPOINT}", status=200,
                                          params=None, body=body("balance_2026-09.json"))])


def test_fetch_asks_each_endpoint_once_per_month_with_explicit_dates():
    http = FixtureHttp()
    out = list(RenSource(periods=("2026-09",)).fetch(all_specs(), http))
    assert http.calls == ["balance_2026-09", "prices_2026-09"]  # (endpoint, month), month asc
    assert [r.status for r in out] == [200, 200]
    m = MANIFEST["sets"]["balance_2026-09"]
    assert out[0].params == {"culture": "pt-PT", "year": "2026", "month": "09"} == m["params"]
    for name, r in zip(http.calls, out):
        assert r.body == body(MANIFEST["sets"][name]["file"])


def test_fetch_of_a_single_family_skips_the_other():
    http = FixtureHttp()
    out = list(RenSource(periods=("2026-09",)).fetch(balance_specs(), http))
    assert http.calls == ["balance_2026-09"] and len(out) == 1


def test_default_periods_are_last_13_completed_months():
    assert RenSource(today=date(2026, 11, 11)).periods == tuple(
        f"2025-{m:02d}" for m in (10, 11, 12)) + tuple(f"2026-{m:02d}" for m in range(1, 11))
    assert "2026-11" not in RenSource(today=date(2026, 11, 30)).periods  # running month out
    assert RenSource(today=date(2026, 1, 5)).periods == ("2024-12",) + tuple(
        f"2025-{m:02d}" for m in range(1, 13))
    assert completed_months(date(2026, 3, 31), 1) == ["2026-02"]


def test_parse_native_code():
    assert parse_native_code("ElectricityConsumptionSupplyMonthly:GAS_NATURAL_CICLO_COMBINADO") == \
        (BALANCE_ENDPOINT, "GAS_NATURAL_CICLO_COMBINADO")
    assert parse_native_code("ElectricityMarketPricesMonthly:PT.Preço Médio") == \
        (PRICES_ENDPOINT, "PT.Preço Médio")


@pytest.mark.parametrize("code", [None, "", "ElectricityConsumptionSupplyMonthly",
                                  "ElectricityConsumptionSupplyMonthly:",
                                  "ElectricityConsumptionSupplyMonthly:consumo",
                                  "ElectricityConsumptionSupplyMonthly:GAS NATURAL",
                                  "ElectricityMarketPricesMonthly:Preço Médio",
                                  "ElectricityMarketPricesMonthly:PT.Preço Médio ",
                                  "ElectricityMarketPricesDaily:PT.Preço Médio",
                                  ":CONSUMO"])
def test_parse_native_code_rejects_malformed(code):
    with pytest.raises(ValueError):
        parse_native_code(code)


def test_registry_native_codes_complete_and_active():
    reg = registry_specs()
    assert len(reg) == 14 and all(s.active and s.url for s in reg.values())
    keys = [parse_native_code(s.native_code) for s in reg.values()]
    assert len(set(keys)) == 14
    assert sum(1 for e, _ in keys if e == BALANCE_ENDPOINT) == 13
    assert sum(1 for e, _ in keys if e == PRICES_ENDPOINT) == 1


def test_validate_roundtrip_units_and_flags():
    parsed = RenSource(periods=("2026-09",)).parse(
        all_specs(), [_raw("balance_2026-09"), _raw("prices_2026-09")])
    by_id = {s.id: s for s in all_specs()}
    for sid, rows in parsed.items():
        obs, rej = validate(by_id[sid], rows)
        assert not rej and {o.status_flag for o in obs} == {"normal"}
        assert obs[0].value_text == EXPECTED_2026_09[sid]


def test_pipeline_quoted_number_fails_validation_and_writes_nothing(tmp_path):
    """End to end: a QUOTED (JSON string) number token in the balance payload is a format
    change -> failed-validation, zero written rows (fail closed at the parse boundary;
    the quoted token would otherwise store AND verify)."""

    class Quoted(FixtureHttp):
        def get(self, url, params=None, headers=None, timeout=None):
            r = super().get(url, params=params, headers=headers, timeout=timeout)
            if self.calls[-1] == "balance_2026-09":
                from ingest.http import HttpResult
                return HttpResult(
                    status=r.status,
                    body=r.body.replace(b'{"monthly_Accumulation":4442,"type":"CONSUMO"}',
                                        b'{"monthly_Accumulation":"04442","type":"CONSUMO"}', 1),
                    url=r.url)
            return r

    specs = all_specs()
    db = open_db(tmp_path / "t.db")
    try:
        sync_registry(db, specs)
        r = run_dataset(db, RawStore(tmp_path / "raw"), RenSource(periods=("2026-09",)), specs,
                        Quoted())
        assert r.state == "failed-validation" and r.n_written == 0
        assert db.conn.execute("SELECT COUNT(*) FROM observation WHERE dataset_run_id=?",
                               (r.run_id,)).fetchone()[0] == 0
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0] == 0
    finally:
        db.close()


def test_pipeline_run_on_fixtures_writes_but_licence_gate_withholds(tmp_path):
    """End to end on recorded bytes: 14 rows written (provenance to each of the 2 payloads);
    even with the run technically flipped to verified, REN's redistribution_ok=false (real
    registry) keeps served=0 — internally verified yet legally withheld."""
    specs = all_specs()
    db = open_db(tmp_path / "t.db")
    try:
        sync_registry(db, specs)
        assert db.conn.execute("SELECT redistribution_ok FROM source WHERE name='ren'") \
            .fetchone()[0] == 0
        r = run_dataset(db, RawStore(tmp_path / "raw"), RenSource(periods=("2026-09",)), specs,
                        FixtureHttp())
        assert r.state == "pending-verification"
        assert r.n_written == 14 and r.n_quarantined == 0
        by_raw = dict(db.conn.execute(
            "SELECT r.url, COUNT(*) FROM observation o JOIN raw_fetch r "
            "ON r.id = o.raw_fetch_id WHERE o.dataset_run_id = ? GROUP BY r.url",
            (r.run_id,)).fetchall())
        assert len(by_raw) == 2  # balance rows carry the balance payload, the price row its own
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0] == 0
        db.set_run_state(r.run_id, "verified", finished_at="2026-11-11T00:00:00+00:00")
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0] == 0
        assert db.conn.execute("SELECT state FROM dataset_run WHERE id=?",
                               (r.run_id,)).fetchone()[0] == "verified"
    finally:
        db.close()
