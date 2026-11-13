"""INE adapter (pindica.jsp JSON, op=2) on recorded real payloads + decoder robustness."""
import json
from collections import Counter
from pathlib import Path

import pytest

from ingest.flags import FLAGS
from ingest.models import SeriesSpec, SourceSpec
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import load_registry, sync_registry
from ingest.sources import RawResponse
from ingest.sources.ine import BASE_URL, PAGE_URL, INESource, parse_native_code
from ingest.validate import validate
from tests.ingest.fakes import FakeHttp, ok
from tests.ingest.ine_fixtures import MANIFEST, FixtureHttp, body, registry_specs, specs_of

REGISTRY = Path(__file__).resolve().parents[2] / "registry" / "core.yaml"
SETS = [name for name in MANIFEST]


def parsed(*sets: str) -> tuple[dict[str, SeriesSpec], dict]:
    specs = specs_of(*sets)
    responses = list(INESource().fetch(specs, FixtureHttp()))
    return {s.id: s for s in specs}, INESource().parse(specs, responses)


def one(rows, period):
    [row] = [r for r in rows if r.period_raw == period]
    return row


# --- fixtures -> rows ----------------------------------------------------------------------------

# Hand cross-check against a THIRD channel (not INE's JSON API) on 2026-11-11: Eurostat's SDMX 2.1
# SDMX-CSV export of the same INE-produced figures,
#   https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/<key>?...&format=SDMX-CSV
#   demo_gind/A.LBIRTH+DEATH+JAN.PT   -> LBIRTH 2024 84642 ; DEATH 2024 118396 ;
#                                        JAN 2025 11387222 (= INE's 31 Dec 2024 estimate)
#   prc_hicp_manr/M.RCH_A.CP00.PT     -> 2025-10 2.0 ; 2025-12 2.4
#   sts_inpr_m/M.PRD.C.SCA.I21.PT     -> 2026-09 96.6 (Eurostat rounds to 1 decimal; INE 96.57)
# INE's `valor` drops trailing zeros: Oct 2025 HICP is '2' (ind_string '2,0', Eurostat 2.0).
# Not on a third channel with the same definition (fixture-only): unemployment 16-74 (Eurostat's
# une_rt_m is 15-74), the confidence indicator, trade by INE's national concept.
EXPECTED = [
    # series id, INE period label, canonical period, value token, flag
    ("ine.live_births.PT", "2024", "2024", "84642", "normal"),
    ("ine.deaths.PT", "2024", "2024", "118396", "normal"),
    ("ine.population.PT", "2024", "2024", "11387222", "normal"),
    ("ine.hicp_yoy.PT", "Outubro de 2025", "2025-10", "2", "normal"),
    ("ine.hicp_yoy.PT", "Dezembro de 2025", "2025-12", "2.4", "normal"),
    ("ine.ipi_seasonal_cae_C.PT", "Setembro de 2026", "2026-09", "96.57", "normal"),
    ("ine.unemployment_monthly.PT", "Setembro de 2026", "2026-09", "5.6", "provisional"),
    ("ine.unemployment_monthly.PT", "Agosto de 2026", "2026-08", "5.6", "normal"),
    ("ine.exports_monthly.PT", "Dezembro de 2024", "2024-12", "5645594514", "normal"),
    ("ine.conf_manufacturing.PT", "Outubro de 2026", "2026-10", "-5.2", "normal"),
]


def test_no_value_cell_is_quarantined_not_guessed():
    # live: IPI food industry (CAE 10) Sept 2026 is 'x' "Dado não disponível" (published later)
    specs, out = parsed("monthly_ipi_0011889")
    row = one(out["ine.ipi_seasonal_cae_10.PT"], "Setembro de 2026")
    assert (row.value_raw, row.flag_raw) == (None, None)
    _, rejected = validate(specs["ine.ipi_seasonal_cae_10.PT"], [row])
    assert [r.reason for r in rejected] == ["non_numeric"]


def test_parse_fixture_yields_expected_rows():
    specs, out = parsed(*SETS)
    assert set(out) == set(specs)
    for sid, label, period, value, flag in EXPECTED:
        row = one(out[sid], label)
        assert (row.value_raw, row.flag_raw, row.unit_raw) == (value, flag, None)
        obs, _ = validate(specs[sid], out[sid])
        [o] = [o for o in obs if o.period == period]
        assert (o.value_text, o.status_flag) == (value, flag)


def test_every_fixture_label_normalises_and_every_row_has_a_flag():
    specs, out = parsed(*SETS)
    for sid, rows in out.items():
        assert rows, sid
        obs, rejected = validate(specs[sid], rows)
        assert {r.reason for r in rejected} <= {"non_numeric"}, (sid, rejected[:3])
        for r in rows:  # value rows carry a flag, no-value rows none
            assert (r.flag_raw in FLAGS) == (r.value_raw is not None), (sid, r)
        assert len(obs) + len(rejected) == len(rows)


def test_parse_preserves_status_flags():
    _, out = parsed(*SETS)
    flags = Counter(r.flag_raw for rows in out.values() for r in rows)
    assert flags["provisional"] >= 1 and flags["normal"] > 100


def test_no_value_signs_become_value_none_rows():
    _, out = parsed(*SETS)
    empty = [r for rows in out.values() for r in rows if r.value_raw is None]
    assert empty and all(r.flag_raw is None for r in empty)


def test_tokens_are_valor_strings_never_floats():
    _, out = parsed(*SETS)
    for rows in out.values():
        for r in rows:
            assert r.value_raw is None or type(r.value_raw) is str


def test_response_index_points_at_the_request_of_each_row():
    specs = specs_of(*SETS)
    responses = list(INESource().fetch(specs, FixtureHttp()))
    out = INESource().parse(specs, responses)
    for s in specs:
        varcd = parse_native_code(s.native_code)[0]
        for r in out[s.id]:
            assert f"varcd={varcd}" in responses[r.response_index].url


def test_fetch_asks_full_history_with_sorted_codes():
    specs = specs_of(*SETS)
    http = FixtureHttp()
    responses = list(INESource().fetch(specs, http))
    assert sorted(http.calls) == sorted(SETS)
    for r in responses:
        assert r.params["Dim1"] == "T" and r.params["op"] == "2" and r.url.startswith(BASE_URL)
        for k, v in r.params.items():
            if k.startswith("Dim") and k != "Dim1":
                assert v.split(",") == sorted(v.split(","))


def test_fetch_forwards_the_source_timeout():
    """Every INE request carries the registry's per-source timeout (core.yaml ine: 300 s)."""
    http = FixtureHttp()
    list(INESource().fetch(specs_of(*SETS), http))
    assert http.timeouts and set(http.timeouts) == {300.0}


def _spec_with_source_timeout(sid: str, timeout_s: float | None) -> SeriesSpec:
    src = SourceSpec(name="ine", licence="CC BY 4.0", licence_url="https://l",
                     attribution="INE", redistribution_ok=True, timeout_s=timeout_s)
    spec = registry_specs()["ine.conf_manufacturing.PT"]
    return spec.model_copy(update={"id": sid, "source": src})


def test_fetch_without_configured_timeout_keeps_legacy_signature():
    """A source with timeout_s None must call Http.get(url, params=...) exactly as before:
    older Http doubles (three parameters) keep working."""
    spec = _spec_with_source_timeout("ine.conf_manufacturing.PT", None)
    http = FakeHttp(ok(b"{}"))
    (response,) = list(INESource().fetch([spec], http))
    assert response.url == "http://fake/data/1"


def test_fetch_with_mixed_timeouts_in_a_group_raises():
    a = _spec_with_source_timeout("ine.a.PT", 300)
    b = _spec_with_source_timeout("ine.b.PT", 60)
    with pytest.raises(ValueError, match="timeout"):
        list(INESource().fetch([a, b], FakeHttp(ok(b"{}"))))


# --- native_code ---------------------------------------------------------------------------------

def test_parse_native_code():
    assert parse_native_code("0011889:Dim2=PT,Dim3=C") == ("0011889", (("Dim2", "PT"), ("Dim3", "C")))
    assert parse_native_code("0001188:Dim2=PT") == ("0001188", (("Dim2", "PT"),))


@pytest.mark.parametrize("code", [None, "", "0011889", "11889:Dim2=PT", "0011889:", "0011889:Dim3=C",
                                  "0011889:Dim2=PT,Dim4=C", "0011889:Dim1=T,Dim2=PT",
                                  "0011889:Dim2=", "0011889:Dim2=P,T", "0011889:Dim2=PT,Dim2=PT",
                                  "abcdefg:Dim2=PT", "0011889:Dim2=PT C"])
def test_parse_native_code_rejects_malformed(code):
    with pytest.raises(ValueError):
        parse_native_code(code)


def test_registry_native_codes_complete():
    """Every active INE series has a parseable native_code and its public page as url;
    inactive ones are explained in registry/unmapped-ine.md."""
    specs = [s for s in load_registry(REGISTRY) if s.source.name == "ine"]
    unmapped = (REGISTRY.parent / "unmapped-ine.md").read_text()
    for s in specs:
        if s.active:
            varcd, _ = parse_native_code(s.native_code)
            assert s.url == PAGE_URL + varcd, s.id
            assert s.decimal == "."  # INE `valor` tokens use '.'
        else:
            assert f"`{s.id}`" in unmapped, s.id


def test_active_native_codes_are_unique():
    codes = Counter(s.native_code for s in load_registry(REGISTRY)
                    if s.source.name == "ine" and s.active)
    assert not [c for c, n in codes.items() if n > 1]


# --- decoder robustness --------------------------------------------------------------------------

SRC = SourceSpec(name="ine", licence="x", licence_url="x", attribution="x", redistribution_ok=True)


def spec(sid="ine.t.PT", code="0001188:Dim2=PT", freq="M"):
    return SeriesSpec(id=sid, source=SRC, indicator_key=sid, role="primary", theme="economy",
                      geography="PT", frequency=freq, unit="%", native_code=code)


def payload(dados, ultimo=None, varcd="0001188", ok=True) -> bytes:
    rec = {"IndicadorCod": varcd, "UltimoPref": ultimo or list(dados)[-1], "Dados": dados}
    rec["Sucesso"] = {"Verdadeiro": [{"Msg": "OK"}]} if ok else {"Falso": [{"Msg": "x"}]}
    return json.dumps([rec], ensure_ascii=False).encode()


def cell(valor="1.5", shown="1,5", **extra):
    c = {"geocod": "PT", "geodsg": "Portugal", "ind_string": shown}
    if valor is not None:
        c["valor"] = valor
    c.update(extra)
    return c


def run_parse(raw: bytes, specs=None):
    specs = specs or [spec()]
    return INESource().parse(specs, [RawResponse(url=BASE_URL, params=None, status=200, body=raw)])


def test_synthetic_happy_path_keeps_label_and_token():
    out = run_parse(payload({"Janeiro de 2025": [cell("2.40", "2,40")],
                             "Fevereiro de 2025": [cell("5", "5,0 &", sinal_conv="&",
                                                        sinal_conv_desc="Dado provisório")],
                             "Março de 2025": [cell(None, "x", sinal_conv="x",
                                                    sinal_conv_desc="Dado não disponível")]}))
    rows = out["ine.t.PT"]
    assert [(r.period_raw, r.value_raw, r.flag_raw) for r in rows] == [
        ("Janeiro de 2025", "2.40", "normal"), ("Fevereiro de 2025", "5", "provisional"),
        ("Março de 2025", None, None)]


def test_thousands_separated_rendering_is_accepted():
    out = run_parse(payload({"2025": [cell("5652560322", "5 652 560 322")]}), [spec(freq="A")])
    assert out["ine.t.PT"][0].value_raw == "5652560322"


@pytest.mark.parametrize("raw", [
    b"<html><head><title>Error</title></head><body>x</body></html>",
    b"\xef\xbb\xbf<!DOCTYPE html><html></html>",
    b"not json", b"{}", b"[]", b"[1]",
    payload({"Janeiro de 2025": [cell()]}, ok=False),
    payload({"Janeiro de 2025": [cell()]}, varcd="0001189"),
    payload({}, ultimo="Janeiro de 2025"),
    payload({"Janeiro de 2025": [cell()]}, ultimo="Fevereiro de 2025"),     # newest period cut
    payload({"Janeiro de 2025": [cell(), cell()]}),                        # duplicate cell
    payload({"Janeiro de 2025": [cell("1.5", "1,6")]}),                    # renderings disagree
    payload({"Janeiro de 2025": [cell("1.5", "1.5")]}),                    # '.' in rendering
    payload({"Janeiro de 2025": [cell("1.5", "1,5", sinal_conv="&",
                                      sinal_conv_desc="Dado provisório")]}),  # sign not shown
    payload({"Janeiro de 2025": [cell("1.5", "1,5 &", sinal_conv="Po",
                                      sinal_conv_desc="Provisório")]}),    # unknown sign
    payload({"Janeiro de 2025": [cell(None, "")]}),                       # no value, no sign
    payload({"Janeiro de 2025": [cell("", "")]}),                         # empty valor
    payload({"Janeiro de 2025": [cell(None, "x", sinal_conv="&",
                                      sinal_conv_desc="Dado provisório")]}),
    payload({"Janeiro de 2025": [cell("1.5", "1,5", dim_3="C", dim_3_t="Ind.")]}),  # extra dim
    payload({"Janeiro de 2025": [{"geocod": "PT", "valor": 1.5, "ind_string": "1,5"}]}),
    payload({"Janeiro de 2025": [{"valor": "1.5", "ind_string": "1,5"}]}),    # no geocod
    payload({"Janeiro de 2025": {"geocod": "PT"}}),
])
def test_parse_rejects_malformed_payloads(raw):
    with pytest.raises(ValueError):
        run_parse(raw)


def test_duplicate_period_keys_raise():
    raw = (b'[{"IndicadorCod":"0001188","UltimoPref":"Janeiro de 2025","Sucesso":{"Verdadeiro":[]},'
           b'"Dados":{"Janeiro de 2025":[{"geocod":"PT","valor":"1","ind_string":"1"}],'
           b'"Janeiro de 2025":[{"geocod":"PT","valor":"2","ind_string":"2"}]}}]')
    with pytest.raises(ValueError, match="duplicate"):
        run_parse(raw)


def test_wrong_response_count_raises():
    with pytest.raises(ValueError):
        INESource().parse([spec()], [])


def test_parse_html_error_page_raises():
    with pytest.raises(ValueError, match="markup"):
        run_parse(body("error_html_page.html"))


@pytest.mark.parametrize("name", ["error_unknown_varcd.json", "error_bad_dim_code.json"])
def test_parse_real_ine_error_objects_raise(name):
    with pytest.raises(ValueError, match="unsuccessful"):
        run_parse(body(name))


# --- through the real pipeline -------------------------------------------------------------------

def test_pipeline_run_on_fixtures_is_pending_verification(tmp_path):
    from ingest.db import open_db
    specs = specs_of(*SETS)
    db = open_db(tmp_path / "t.db")
    try:
        sync_registry(db, specs)
        res = run_dataset(db, RawStore(tmp_path / "raw"), INESource(), specs, FixtureHttp())
        assert res.state == "pending-verification" and res.n_written > 0
        n_q = db.conn.execute("SELECT COUNT(*) FROM quarantine WHERE reason='non_numeric'").fetchone()[0]
        assert n_q == res.n_quarantined
        # nothing is served before verify_run passes (see tests/ingest/test_verifier_ine.py for
        # the verified end-to-end run on the independent bddXplorer channel)
        assert db.conn.execute("SELECT COUNT(*) FROM served_observation").fetchone()[0] == 0
    finally:
        db.close()


def test_ine_has_an_independent_channel_and_a_verifier():
    """Task 10 fix round 1 (review finding C1): INE DOES have an independent channel — the
    bddXplorer server-rendered table (Referer header) is a different endpoint+format from the
    collector's JSON API — and ingest/verifiers/ine.py implements it."""
    from ingest.verifiers.ine import PAGE_URL as VERIFIER_URL
    from ingest.verifiers.ine import INEVerifier
    root = REGISTRY.parent
    assert "## ine" not in (root / "unverifiable.md").read_text()
    assert (root.parent / "ingest" / "verifiers" / "ine.py").exists()
    assert INEVerifier.source_name == "ine"
    assert VERIFIER_URL.startswith("https://www.ine.pt/bddXplorer/")
    assert VERIFIER_URL != BASE_URL  # a different endpoint than the collector's JSON API
