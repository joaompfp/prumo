"""Eurostat adapter (JSON-stat, Statistics API 1.0) on recorded real payloads."""
import json
import re
from pathlib import Path

import pytest

from ingest.flags import FLAGS
from ingest.models import SeriesSpec
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources import RawResponse
from ingest.sources.eurostat import BASE_URL, EurostatSource, parse_native_code
from ingest.validate import validate
from tests.ingest.eurostat_fixtures import FIX, MANIFEST, FixtureHttp, body, specs_of
from tests.ingest.fakes import FakeHttp, ok

# the four base sets (one per frequency); the confidential_* sets are tested on their own
ALL = ["monthly_sts_inpr_m", "annual_nama_10_pc", "quarterly_namq_10_gdp", "semester_nrg_pc_204"]
REGISTRY = Path(__file__).resolve().parents[2] / "registry"


def parsed(*sets: str) -> tuple[dict[str, SeriesSpec], dict]:
    specs = specs_of(*sets)
    responses = list(EurostatSource().fetch(specs, FixtureHttp()))
    return {s.id: s for s in specs}, EurostatSource().parse(specs, responses)


def one(rows, period):
    [row] = [r for r in rows if r.period_raw == period]
    return row


# --- fixtures -> rows ----------------------------------------------------------------------------

# Each expected observation was cross-checked by hand against a THIRD Eurostat channel, the SDMX
# 2.1 SDMX-CSV export (OBS_VALUE / OBS_FLAG columns), on 2026-11-11:
#   https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/<key below>&format=SDMX-CSV
#   sts_inpr_m/M.PRD.B-D.SCA.I21.PT?startPeriod=2026-09               -> 2026-09,97.1,(none)
#   sts_inpr_m/M.PRD.B-D.SCA.I21.PT+EU27_2020?startPeriod=1991-01&endPeriod=1991-01
#                                                         -> EU27_2020,1991-01,74.8,i
#   nama_10_pc/A.CP_EUR_HAB.B1GQ.PT+EU27_2020?startPeriod=2020 -> PT,2025,28560,p ;
#                                                               EU27_2020,2020,30560,b
#   namq_10_gdp/Q.CLV10_MEUR.SCA.B1GQ.EU27_2020?startPeriod=2026-Q3 -> 2026-Q3,3471512.8,(none)
#   nrg_pc_204/S.E7000.KWH2500-4999.KWH.I_TAX.EUR.PT+EL?startPeriod=2019-S1&endPeriod=2021-S1
#                                                         -> PT,2019-S1,0.2150 ; EL,2021-S1,0.1680
# ('i' = "value imputed by Eurostat or other receiving agencies", from the payload's
#  extension.status.label.)
EXPECTED = [
    # series id, Eurostat period, canonical period, value token, registry unit, status flag
    ("eurostat.STS_INPR_M_BD.PT", "2026-09", "2026-09", "97.1", "I21", "normal"),
    ("eurostat.ipi_total.EU27", "1991-01", "1991-01", "74.8", "index_2021", "estimated"),
    ("eurostat.gdp_per_capita_eur.PT", "2025", "2025", "28560", "EUR per capita", "provisional"),
    ("eurostat.gdp_per_capita_eur.EU27_2020", "2020", "2020", "30560", "EUR per capita", "break"),
    ("eurostat.gdp_quarterly.EU27", "2026-Q3", "2026-Q3", "3471512.8", "M_EUR_2010", "normal"),
    ("eurostat.electricity_price_household.PT", "2019-S1", "2019-S1", "0.2150", "EUR/kWh",
     "normal"),
    ("eurostat.electricity_price_household.GR", "2021-S1", "2021-S1", "0.1680", "EUR/kWh",
     "normal"),
]


def test_parse_fixture_yields_expected_rows():
    specs, out = parsed(*ALL)
    assert set(out) == set(specs)
    for sid, period_raw, period, value, unit, flag in EXPECTED:
        row = one(out[sid], period_raw)
        assert (row.value_raw, row.flag_raw, row.unit_raw) == (value, flag, None)
        # validate() (the pipeline's next step) turns it into exactly this observation
        obs, rejected = validate(specs[sid], out[sid])
        assert not rejected
        [o] = [o for o in obs if o.period == period]
        assert (o.value_text, o.status_flag) == (value, flag)
        assert specs[sid].unit == unit  # unit_raw None: the registry unit is authoritative


def test_parse_keeps_publisher_tokens_verbatim():
    # '0.2150' must not become '0.215' (Ruling J): numbers are handed over as JSON tokens
    _, out = parsed("semester_nrg_pc_204")
    assert one(out["eurostat.electricity_price_household.PT"], "2019-S1").value_raw == "0.2150"
    assert all(type(r.value_raw) is str for rows in out.values() for r in rows)
    assert b"0.2150" in body("semester_nrg_pc_204.json")


def test_parse_covers_every_period_in_order_with_response_index():
    _, out = parsed(*ALL)
    rows = out["eurostat.STS_INPR_M_BD.DE"]
    assert [r.period_raw for r in rows][:2] == ["1991-01", "1991-02"]
    assert rows[-1].period_raw == "2026-09" and len(rows) == 429
    # four datasets -> four responses, ordered by dataset; rows point at their own response
    order = ["nama_10_pc", "namq_10_gdp", "nrg_pc_204", "sts_inpr_m"]
    for sid, rows in out.items():
        [idx] = {r.response_index for r in rows}
        dataset = parse_native_code(next(s for s in specs_of(*ALL) if s.id == sid).native_code)[0]
        assert idx == order.index(dataset), sid


def test_series_sharing_a_key_get_the_same_rows():
    _, out = parsed("monthly_sts_inpr_m")
    a, b, c = (out[f"eurostat.{x}.PT"] for x in ("STS_INPR_M_BD", "ipi", "total_industry"))
    assert a == b == c and a


def test_parse_preserves_status_flags():
    _, out = parsed(*ALL)
    flags = {r.flag_raw for rows in out.values() for r in rows}
    assert {"normal", "provisional", "estimated", "break"} <= flags <= set(FLAGS)
    de = {r.period_raw: r.flag_raw for r in out["eurostat.gdp_per_capita_eur.DE"]}
    assert (de["2022"], de["2023"], de["2024"], de["2025"]) == (
        "normal", "provisional", "provisional", "provisional")


@pytest.mark.parametrize("name, sid, code, n_conf, example", [
    # STS_INPR_M_C.IE: 60 cells labelled '|C' (confidential), e.g. 2014-12
    ("confidential_c_sts_inpr_m", "eurostat.STS_INPR_M_C.IE", "|C", 60, "2014-12"),
    # metals.PT (C24_C25): 2 cells labelled '|N' (not for publication), e.g. 2026-09
    ("confidential_n_sts_inpr_m", "eurostat.metals.PT", "|N", 2, "2026-09"),
])
def test_confidential_cells_become_value_none_rows(name, sid, code, n_conf, example):
    doc = json.loads(body(f"{name}.json"))
    assert list(doc["status"].values()).count(code) == n_conf
    assert doc["extension"]["status"]["label"][code] in ("|confidential", "|not for publication")
    specs, out = parsed(name)
    rows = out[sid]
    none_rows = [r for r in rows if r.value_raw is None]
    assert len(none_rows) == n_conf and all(r.flag_raw is None for r in none_rows)
    assert one(rows, example).value_raw is None
    others = [r for r in rows if r.value_raw is not None]
    assert others and all(r.flag_raw in FLAGS for r in others)
    obs, rejected = validate(specs[sid], rows)
    assert len(rejected) == n_conf and {x.reason for x in rejected} == {"non_numeric"}
    assert len(obs) == len(others)


@pytest.mark.parametrize("status", ["b|C", "p|N", "|C"])
def test_confidentiality_hides_the_value_whatever_the_flag(status):
    rows = _parse_toy(_cube({"2": 9, "3": 5}, {"2": status}))
    assert [(r.period_raw, r.value_raw, r.flag_raw) for r in rows] == [
        ("2023", None, None), ("2024", "5", "normal")]


@pytest.mark.parametrize("status", ["|X", "b|Q", "x|C"])
def test_unknown_confidentiality_or_flag_raises(status):
    with pytest.raises(ValueError):
        _parse_toy(_cube({"3": 5}, {"2": status}))


# --- fetch ---------------------------------------------------------------------------------------

def test_fetch_one_request_per_dataset_key_with_all_geos():
    http = FixtureHttp()
    responses = list(EurostatSource().fetch(specs_of(*ALL), http))
    assert len(responses) == 4 == len(http.calls)
    assert sorted(r.url for r in responses) == sorted(MANIFEST[n]["json_url"] for n in ALL)
    sts = next(r for r in responses if "sts_inpr_m" in r.url)
    assert sts.params == {"freq": "M", "indic_bt": "PRD", "nace_r2": "B-D", "s_adj": "SCA",
                          "unit": "I21", "geo": ["CZ", "DE", "EU27_2020", "PT"]}
    assert all(r.status == 200 and r.url.startswith(BASE_URL) for r in responses)


def test_fetch_splits_different_keys_of_one_dataset():
    reg = {s.id: s for s in specs_of(*ALL)}
    other = reg["eurostat.STS_INPR_M_BD.PT"].model_copy(update={
        "id": "x", "native_code": "sts_inpr_m:freq=M,indic_bt=PRD,nace_r2=C,s_adj=SCA,unit=I21,"
                                  "geo=PT"})
    http = FakeHttp(ok(b"{}"), ok(b"{}"))
    responses = list(EurostatSource().fetch([reg["eurostat.STS_INPR_M_BD.PT"], other], http))
    assert [p["nace_r2"] for _, p in http.calls] == ["B-D", "C"] and len(responses) == 2


# --- failures --------------------------------------------------------------------------------------

def _parse_body(raw: bytes, sets=("quarterly_namq_10_gdp",)):
    specs = specs_of(*sets)
    url = MANIFEST[sets[0]]["json_url"]
    return EurostatSource().parse(specs, [RawResponse(url, None, 200, raw)])


@pytest.mark.parametrize("raw", [
    body("html_404_not_found.html"),  # real body Eurostat sends for an unknown API path
    b"<!DOCTYPE html><html><head><title>Service unavailable</title></head><body>Maintenance"
    b"</body></html>",  # synthetic: the shape of a maintenance page
    body("sdmx_404_fault.xml"),  # real XML fault (from the SDMX endpoint)
    b"",
])
def test_parse_html_error_page_raises(raw):
    with pytest.raises(ValueError):
        _parse_body(raw)


@pytest.mark.parametrize("name", ["error_404_unknown_dataset.json", "error_413_async.json"])
def test_parse_json_error_object_raises(name):
    with pytest.raises(ValueError, match="error object"):
        _parse_body(body(name))


def test_unknown_flag_raises():
    raw = body("annual_nama_10_pc.json").replace(b'"p"', b'"x"', 1)
    assert raw != body("annual_nama_10_pc.json")
    with pytest.raises(ValueError, match="unknown Eurostat flag"):
        _parse_body(raw, ("annual_nama_10_pc",))


def test_unknown_flag_fails_the_dataset_run(db, tmp_path):
    specs = specs_of("annual_nama_10_pc")
    sync_registry(db, specs)
    raw = body("annual_nama_10_pc.json").replace(b'"p"', b'"x"', 1)
    url = MANIFEST["annual_nama_10_pc"]["json_url"]
    r = run_dataset(db, RawStore(tmp_path / "raw"), EurostatSource(), specs,
                    FixtureHttp({url: raw}))
    assert r.state == "failed-validation" and r.n_written == 0


def test_dimension_mismatch_raises():
    doc = json.loads(body("quarterly_namq_10_gdp.json"))
    doc["id"] = [d if d != "s_adj" else "seasonal" for d in doc["id"]]
    doc["dimension"]["seasonal"] = doc["dimension"].pop("s_adj")
    with pytest.raises(ValueError, match="do not match native_code"):
        _parse_body(json.dumps(doc).encode())


def test_size_index_mismatch_raises():
    doc = json.loads(body("quarterly_namq_10_gdp.json"))
    doc["size"][-1] += 1
    with pytest.raises(ValueError, match="does not match size"):
        _parse_body(json.dumps(doc).encode())


def test_wrong_number_of_responses_raises():
    specs = specs_of("quarterly_namq_10_gdp")
    with pytest.raises(ValueError, match="expected 1"):
        EurostatSource().parse(specs, [])


def test_response_for_another_dataset_raises():
    with pytest.raises(ValueError, match="expected dataset"):
        EurostatSource().parse(specs_of("quarterly_namq_10_gdp"), [RawResponse(
            MANIFEST["annual_nama_10_pc"]["json_url"], None, 200, body("annual_nama_10_pc.json"))])


# --- JSON-stat shapes (synthetic, minimal) -----------------------------------------------------------

def _cube(value, status=None, geos=("PT", "ES"), times=("2023", "2024")):
    doc = {"version": "2.0", "class": "dataset", "id": ["freq", "unit", "geo", "time"],
           "size": [1, 1, len(geos), len(times)],
           "dimension": {"freq": {"category": {"index": {"A": 0}}},
                         "unit": {"category": {"index": {"PC": 0}}},
                         "geo": {"category": {"index": {g: i for i, g in enumerate(geos)}}},
                         "time": {"category": {"index": {t: i for i, t in enumerate(times)}}}},
           "value": value}
    if status is not None:
        doc["status"] = status
    return json.dumps(doc).replace('"__TOKEN__"', "1.10").encode()


def _toy(code="toy:freq=A,unit=PC,geo=ES"):
    base = specs_of("annual_nama_10_pc")[0]
    return base.model_copy(update={"id": code, "native_code": code})


def _parse_toy(raw, code="toy:freq=A,unit=PC,geo=ES"):
    url = BASE_URL + "toy?freq=A"
    return EurostatSource().parse([_toy(code)], [RawResponse(url, None, 200, raw)])[code]


def test_flat_index_is_row_major_over_id_order():
    # ES is geo position 1: flat = 1 * 2 (time size) + time position
    rows = _parse_toy(_cube({"0": 1, "1": 2, "2": 3, "3": 4}))
    assert [(r.period_raw, r.value_raw) for r in rows] == [("2023", "3"), ("2024", "4")]


def test_array_valued_value_and_trailing_zero_token():
    rows = _parse_toy(_cube([1, 2, 3, "__TOKEN__"]))
    assert rows[-1].value_raw == "1.10"


def test_status_without_value_is_a_none_row_and_absent_cells_are_skipped():
    rows = _parse_toy(_cube({"3": 5}, {"2": ":"}))
    assert [(r.period_raw, r.value_raw, r.flag_raw) for r in rows] == [
        ("2023", None, None), ("2024", "5", "normal")]
    rows = _parse_toy(_cube({"3": 5}, {"2": "c"}))
    assert rows[0].value_raw is None


def test_no_value_marker_on_a_value_raises():
    with pytest.raises(ValueError, match="only accompany a missing value"):
        _parse_toy(_cube({"3": 5}, {"3": "c"}))


def test_geo_absent_from_response_gives_no_rows():
    assert _parse_toy(_cube({"0": 1}, geos=("PT",)), "toy:freq=A,unit=PC,geo=ES") == []


@pytest.mark.parametrize("code", [None, "", "toy", "toy:", ":geo=PT", "toy:geo", "toy:unit=PC",
                                  "toy:geo=PT,geo=ES", "toy:geo=PT,time=2020", "toy:geo=P=T"])
def test_malformed_native_code_raises(code):
    with pytest.raises(ValueError):
        parse_native_code(code)


# --- registry ----------------------------------------------------------------------------------------

def test_registry_native_codes_complete():
    """Every active Eurostat series has a parseable native_code pinning one series, and a url;
    every inactive one is explained in registry/unmapped-eurostat.md."""
    specs = [s for s in load_registry(REGISTRY / "core.yaml") if s.source.name == "eurostat"]
    unmapped = (REGISTRY / "unmapped-eurostat.md").read_text()
    dims_of: dict[str, list[str]] = {}
    for s in specs:
        if not s.active:
            assert s.id in unmapped, s.id
            continue
        dataset, key = parse_native_code(s.native_code)
        dims = [d for d, _ in key]
        assert dims_of.setdefault(dataset, dims) == dims, f"{s.id}: inconsistent dimensions"
        assert dict(key)["freq"] == s.frequency, s.id
        assert s.url == f"https://ec.europa.eu/eurostat/databrowser/view/{dataset}/default/table?lang=en"
        assert re.fullmatch(r"[a-z0-9_]+", dataset), s.id
    # the dimensions pinned equal the dataset's real dimensions where we hold a payload
    for name in ALL:
        doc = json.loads(body(f"{name}.json"))
        dataset = doc["extension"]["id"].lower()
        assert dims_of[dataset] == [d for d in doc["id"] if d != "time"]
    active = [s for s in specs if s.active]
    assert len(active) == 598 and len(specs) - len(active) == 99
    assert len({s.id for s in active}) == len(active)


def test_fixtures_are_small():
    assert all(f.stat().st_size <= 200_000 for f in FIX.iterdir())
