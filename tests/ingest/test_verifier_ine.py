"""INE independent verifier (bddXplorer04.jsp server-rendered table) on recorded real fixtures,
alone and through the full pipeline (run_dataset on the recorded JSON payloads -> verify_run
with the recorded HTML selections -> verified).

All fixture values were recorded live 2026-11-11 and cross-checked (see the cross_check notes in
tests/ingest/fixtures/ine/verify/MANIFEST.json): 18/20 against the collector's own recorded JSON
fixtures (value as exact Decimal + sign-mapped flag), 2 against a live JSON fetch taken during
recording, and births/deaths/population/HICP additionally against Eurostat's SDMX TSV.
"""
import re
from datetime import datetime, timedelta, timezone

import pytest

from ingest import verifiers
from ingest.pipeline import run_dataset
from ingest.rawstore import RawStore
from ingest.registry import sync_registry
from ingest.sources.ine import INESource
from ingest.verifiers import BlindItem, get_verifier, register_verifier
from ingest.verifiers.independence import assert_verifier_independent
from ingest.verifiers.ine import INEVerifier
from ingest.verify import run_with_refetch, verify_run
from tests.ingest.fakes import FakeHttp, ok
from tests.ingest.ine_fixtures import FixtureHttp, body, registry_specs, specs_of
from tests.ingest.ine_verifier_fixtures import VMANIFEST, VerifyFixtureHttp, vbody

# JSON fixture sets the clean pipeline run below is built from; the verifier sample (seed 7,
# size 12) only asks for cuts whose selections are recorded in VMANIFEST.
SETS = ["monthly_unemployment_0007983", "annual_births_0001346", "monthly_exports_0001400",
        "monthly_ipi_0011889"]


class Clock:
    def __init__(self):
        self.t = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(verifiers, "_REGISTRY", {})


def q(db, sql, *args):
    return db.conn.execute(sql, args).fetchall()


def blind(sid, period):
    return BlindItem(sid, period, registry_specs()[sid])


# --- the channel -------------------------------------------------------------------------------

def test_verifier_reads_every_recorded_case():
    results = INEVerifier().check(
        [blind(c["series"], c["period"]) for c in VMANIFEST["cases"].values()],
        VerifyFixtureHttp())
    assert len(results) == len(VMANIFEST["cases"])
    for (key, case), r in zip(VMANIFEST["cases"].items(), results):
        o = case["observed"]
        got = (r.series_id, r.period, r.observed_text, r.observed_decimal, r.observed_unit,
               r.observed_flag)
        assert got == (case["series"], case["period"], o["text"], ",", o["unit"], o["flag"]), key
        assert "bddXplorer04.jsp" in r.evidence_url
        assert r.evidence == vbody(VMANIFEST["routes"][case["route"]]["file"])


def test_verifier_period_and_identity_come_from_the_evidence():
    """A request for a period the table doesn't answer raises instead of echoing."""
    with pytest.raises(ValueError, match="offered 0x"):
        INEVerifier().check([blind("ine.live_births.PT", "1800")], VerifyFixtureHttp())


def test_verifier_wrong_dimension_selection_fails_closed():
    """The response's echoed selection must equal the pinned cut: a response for another cut
    (here Dim3=T served against a Dim3=1 request) raises instead of being read."""
    spec = registry_specs()["ine.live_births.PT"].model_copy(
        update={"native_code": "0001346:Dim2=PT,Dim3=1"})
    http = VerifyFixtureHttp(alias={("sel", "0001346", ("2024",), ("1", "PT")):
                                    "sel_0001346_2024_PT_T"})
    with pytest.raises(ValueError, match="selection"):
        INEVerifier().check([BlindItem(spec.id, "2024", spec)], http)


def test_verifier_unknown_sign_in_cell_raises():
    raw = vbody("sel_0007983_Setembro_de_2026_PT_T.html").replace(b"5,6 &amp;", b"5,6 \xe2\x9c\x95")
    assert b"5,6 &amp;" in vbody("sel_0007983_Setembro_de_2026_PT_T.html")
    with pytest.raises(ValueError, match="unreadable"):
        INEVerifier().check([blind("ine.unemployment_monthly.PT", "2026-09")],
                            VerifyFixtureHttp({"sel_0007983_Setembro_de_2026_PT_T": raw}))


def test_verifier_unit_symbol_change_raises():
    raw = vbody("sel_0001346_2024_PT_T.html").replace(b"<th scope='col' class='THeader'>N.\xc2\xba </th>",
                                                      b"<th scope='col' class='THeader'>\xe2\x82\xac </th>")
    assert raw != vbody("sel_0001346_2024_PT_T.html"), "unit cell not found for mutation"
    with pytest.raises(ValueError, match="unit symbol"):
        INEVerifier().check([blind("ine.live_births.PT", "2024")],
                            VerifyFixtureHttp({"sel_0001346_2024_PT_T": raw}))


def test_verifier_potencia_scaling_raises():
    raw = re.sub(rb"potencia='0'", b"potencia='1'", vbody("sel_0001346_2024_PT_T.html"))
    assert raw != vbody("sel_0001346_2024_PT_T.html")
    with pytest.raises(ValueError, match="potencia"):
        INEVerifier().check([blind("ine.live_births.PT", "2024")],
                            VerifyFixtureHttp({"sel_0001346_2024_PT_T": raw}))


def test_verifier_wrong_period_label_in_table_raises():
    raw = vbody("sel_0001346_2024_PT_T.html").replace(b"<b>2024</b>", b"<b>2023</b>")
    assert raw != vbody("sel_0001346_2024_PT_T.html")
    with pytest.raises(ValueError, match="period"):
        INEVerifier().check([blind("ine.live_births.PT", "2024")],
                            VerifyFixtureHttp({"sel_0001346_2024_PT_T": raw}))


def test_verifier_error_page_raises():
    http = FakeHttp(ok(vbody("error_page_ora.html")), ok(vbody("error_page_ora.html")))
    with pytest.raises(ValueError, match="only 1970 B"):
        INEVerifier().check([blind("ine.live_births.PT", "2024")], http)


def test_verifier_home_redirect_without_referer_raises():
    """What INE answers when the Referer is missing (302 followed to the home page): no
    xmlDocHidden, no dados table — a loud failure, never a pass."""
    http = FakeHttp(ok(vbody("home_no_referer.html")))
    with pytest.raises(ValueError):
        INEVerifier().check([blind("ine.live_births.PT", "2024")], http)


def test_verifier_http_error_status_raises():
    with pytest.raises(ValueError, match="HTTP 500"):
        INEVerifier().check([blind("ine.live_births.PT", "2024")],
                            FakeHttp(ok(b"", status=500)))


def test_verifier_no_value_cell_is_not_found():
    """'x' instead of the value: observed None + no flag (a mismatch if sampled — the JSON
    channel quarantines such cells, so clean runs never sample them)."""
    raw = vbody("sel_0011889_Junho_de_2026_10_PT.html").replace(b">114,57<", b">x<")
    assert raw != vbody("sel_0011889_Junho_de_2026_10_PT.html")
    (r,) = INEVerifier().check([blind("ine.ipi_seasonal_cae_10.PT", "2026-06")],
                               VerifyFixtureHttp({"sel_0011889_Junho_de_2026_10_PT": raw}))
    assert (r.observed_text, r.observed_flag, r.observed_unit) == (None, None, "index_2021=100")


def test_verifier_multiple_signs_take_the_strongest():
    raw = vbody("sel_0007983_Setembro_de_2026_PT_T.html").replace(b"5,6 &amp;", b"5,6 &amp; &#167;")
    (r,) = INEVerifier().check([blind("ine.unemployment_monthly.PT", "2026-09")],
                               VerifyFixtureHttp({"sel_0007983_Setembro_de_2026_PT_T": raw}))
    assert (r.observed_text, r.observed_flag) == ("5,6", "provisional")  # § is 'normal'-mapped


def test_verifier_deep_category_selection_uses_the_injection(tmp_path):
    """CAE divisions are absent from the shipped tree: the request's xmlDocHidden for a division
    (Dim3=08 here) must contain an injected Categoria node."""
    from ingest.verifiers.ine import _page_from, _select
    page = _page_from(vbody("page_0011889.html"), "0011889")
    form = _select(page, "2026-06", "M", [("Dim2", "PT"), ("Dim3", "08")])
    assert "cod_categ='08'" in form["xmlDocHidden"] or 'cod_categ="08"' in form["xmlDocHidden"]
    # and the recorded response verifies as usual
    (r,) = INEVerifier().check([blind("ine.ipi_seasonal_cae_08.PT", "2026-06")],
                               VerifyFixtureHttp())
    assert r.observed_text == "124,88"


# --- registration and independence -------------------------------------------------------------

def test_verifier_registers_and_passes_allowlist():
    v = INEVerifier()
    register_verifier(v)  # static allowlist + no shared module with ingest/sources/ine.py
    assert get_verifier("ine") is v


def test_subprocess_independence():
    assert_verifier_independent("ingest.verifiers.ine",
                                "tests.ingest.ine_verifier_entry:run",
                                source_name="ine",
                                blocked_prefixes=("collectors", "ingest.flags", "ingest.sources"))


# --- through the pipeline -----------------------------------------------------------------------

@pytest.fixture
def env(db, tmp_path):
    specs = specs_of(*SETS)
    sync_registry(db, specs)
    return db, specs, RawStore(tmp_path / "raw"), Clock()


def test_verifier_matches_clean_run(env):
    db, specs, store, clock = env
    r = run_dataset(db, store, INESource(), specs, FixtureHttp(), clock)
    assert r.state == "pending-verification" and r.n_written > 1000
    assert verify_run(db, r.run_id, INEVerifier(), VerifyFixtureHttp(), seed=7, size=12,
                      specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "verified"
    [(n, passed)] = q(db, "SELECT sample_size, passed FROM verification WHERE dataset_run_id=?",
                      r.run_id)
    assert passed == 1 and n == 12
    # every sampled item compared value AND unit AND flag, and its evidence (the selection HTML)
    # is kept in the raw store
    assert q(db, "SELECT COUNT(*) FROM verification_item WHERE observed_unit IS NULL "
                 "OR observed_flag IS NULL OR evidence_sha256 IS NULL") == [(0,)]
    units = {u for (u,) in q(db, "SELECT DISTINCT observed_unit FROM verification_item")}
    assert units == {"%", "EUR", "N.º", "index_2021=100"}
    flags = {f for (f,) in q(db, "SELECT DISTINCT observed_flag FROM verification_item")}
    assert "provisional" in flags  # '5,6 &' on the latest unemployment month
    served = q(db, "SELECT COUNT(*) FROM served_observation WHERE series_id LIKE 'ine.%'")
    assert served[0][0] > 0


def test_verifier_detects_tampered_value(env):
    """The JSON payload is tampered (valor AND its ind_string, else the adapter's own consistency
    check would reject it); the verifier reads the untampered table and the run fails."""
    db, specs, store, clock = env
    raw = body("annual_births_0001346.json")
    assert raw.count(b'"valor" : "87764"') == 1 and raw.count(b'"ind_string" : "87 764"') == 1
    tampered = raw.replace(b'"valor" : "87764"', b'"valor" : "87765"') \
                  .replace(b'"ind_string" : "87 764"', b'"ind_string" : "87 765"')
    r = run_dataset(db, store, INESource(), specs,
                    FixtureHttp({"annual_births_0001346": tampered}), clock)
    assert r.state == "pending-verification"
    assert not verify_run(db, r.run_id, INEVerifier(), VerifyFixtureHttp(), seed=7, size=12,
                          specs=specs, store=store, now=clock)
    assert db.run_state(r.run_id) == "failed-verification"
    bad = q(db, "SELECT series_id, period, expected_text, observed_text, note FROM "
                "verification_item WHERE match=0")
    assert bad == [("ine.live_births.PT", "2025", "87765", "87 764", "value differs")]
    assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]


class _BothChannels:
    """run_with_refetch shares one Http between collector and verifier: dispatch by path."""

    def __init__(self):
        self.collector = FixtureHttp()
        self.verifier = VerifyFixtureHttp()

    def get(self, url, params=None, headers=None, timeout=None):
        if "bddXplorer" in url:
            return self.verifier.get(url, params=params, headers=headers, timeout=timeout)
        return self.collector.get(url, params=params, headers=headers, timeout=timeout)


def test_run_with_refetch_uses_registered_verifier(env):
    """Only the registered verifier may pass; the verified happy path runs live
    (tests/ingest/test_live_ine.py): a random-seeded sample space can't be recorded."""
    db, specs, store, clock = env
    v = INEVerifier()
    register_verifier(v)
    res = run_with_refetch(db, store, INESource(), v, specs, _BothChannels(), size=12, now=clock,
                           max_attempts=1)
    [(passed,)] = q(db, "SELECT passed FROM verification")
    if not passed:
        # cuts outside the recorded ones fail the run loudly (the fake answers AssertionError),
        # never a false pass and nothing served
        assert res.state == "failed-verification"
        assert q(db, "SELECT COUNT(*) FROM served_observation") == [(0,)]
        notes = [n for (n,) in q(db, "SELECT note FROM verification_item WHERE match=0")]
        assert any("no recorded verifier response" in (n or "") for n in notes)
    else:
        assert res.state == "verified"
