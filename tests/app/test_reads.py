"""Page composition on a real (synthetic) database: titles, provenance, filters and cards."""
import json

import pytest

from app import reads
from ingest.models import Observation, SourceSpec
from ingest.registry import sync_derived, sync_registry
from presentation.catalog import pt
from tests.ingest.derived_helpers import derived_spec

T1 = "2026-11-01T00:00:00+00:00"
T2 = "2026-11-02T00:00:00+00:00"
T3 = "2026-11-03T00:00:00+00:00"
INE = SourceSpec(name="ine", licence="CC BY 4.0", licence_url="https://ine.pt/licenca",
                 attribution="Fonte: INE", redistribution_ok=True)
EURO = SourceSpec(name="eurostat", licence="CC BY 4.0",
                  licence_url="https://ec.europa.eu/eurostat/copyright",
                  attribution="Source: Eurostat", redistribution_ok=True)
REN = SourceSpec(name="ren", licence="Sem reutilização", licence_url="https://ren.pt/termos",
                 attribution="Source: REN", redistribution_ok=False)
KEY = "derived.population.PT.yoy_change_pct"


def _spec(sid, *, source=INE, key="ine_population.PT.M", role="primary", active=True):
    from tests.ingest.fakes import spec
    return spec(sid, frequency="M").model_copy(
        update={"source": source, "indicator_key": key, "role": role, "active": active,
                "unit": "%", "geography": "PT", "theme": "economy"})


def _verified(db, sid, period, value, fetched_at, key, *, source="ine"):
    run = db.begin_run(source, key, fetched_at)
    fid = db.record_raw_fetch(source_name=source, run_id=run, url=f"https://{source}/x",
                              params_json=None, fetched_at=fetched_at, http_status=200,
                              sha256=f"sha-{key}", path="p", n_bytes=100, ok=True)
    db.write_observations(run, [(Observation.from_raw(sid, period, value), fid, fetched_at)])
    db.set_run_state(run, "verified")
    return run


@pytest.fixture
def db(tmp_path):
    from ingest.db import open_db
    handle = open_db(tmp_path / "prumo.db")
    yield handle
    handle.close()


@pytest.fixture
def page_db(db):
    reads.clear_cache()
    sync_registry(db, [_spec("s1"), _spec("s2", source=EURO, role="cross_check"),
                       _spec("s3", source=REN)])
    _verified(db, "s1", "2026-01", "5.9", T1, "k1")
    _verified(db, "s1", "2026-02", "5.6", T2, "k2")
    run = _verified(db, "s1", "2026-02", "5.7", T3, "k3")  # a revision; served is 5.7
    _verified(db, "s2", "2026-02", "5.65", T2, "kc", source="eurostat")
    _verified(db, "s3", "2026-02", "9.9", T2, "kw", source="ren")
    v = db.add_verification(run, 42, 10, True, T2, sample_procedure="prumo-sample-v2",
                            sample_design={"n_items": 10}, input_origin="live",
                            verifier_channel="live")
    db.add_verification_item(v, {
        **{c: None for c in ("expected_text", "expected_decimal", "expected_unit",
                             "expected_flag", "observed_series_id", "observed_period",
                             "observed_text", "observed_decimal", "observed_unit",
                             "observed_flag", "evidence_url", "evidence_sha256", "note",
                             "reason", "compared", "unit_not_compared", "flag_not_compared")},
        "series_id": "s1", "period": "2026-02", "match": True})
    sync_derived(db, [derived_spec(KEY, "s1", "yoy_change_pct")])
    inputs = db.served_fetched_inputs("s1")
    dsid = next(r["id"] for r in db.derived_series_rows(active_only=False) if r["key"] == KEY)
    drun = db.begin_derived_run(T3, "cli", [KEY])
    db.write_derived_observations(drun, T3, [(dsid, "2026-02", "0.3", 1,
                                              json.dumps([inputs["2026-02"][0],
                                                          inputs["2026-01"][0]]))])
    oid = db.derived_observations_of_run(drun)[-1]["id"]
    db.set_derived_row_states([(oid, "match")])
    db.finish_derived_run(drun, "verified", T3, n_written=1, n_checked=1, n_mismatch=0)
    yield db
    reads.clear_cache()


def test_series_page_composes_title_provenance_revision_and_derived(page_db):
    page = reads.series_page(page_db, "s1")
    assert page.series.title == "População residente - Portugal"
    assert page.series.frequency_text == "Mensal" and page.series.unit_text == "%"
    assert page.series.latest.value_display == "5,7"
    assert page.series.source_title == "INE - Instituto Nacional de Estatística"
    assert page.provenance.value_display == "5,7" and page.provenance.sampled is True
    assert page.provenance.sha256 == "sha-k3"
    assert page.provenance.verification_created_text == "02/11/2026, 00:00 UTC"
    assert page.revised_periods == 1
    assert [v.value_display for v in page.revisions[0].versions] == ["5,6", "5,7"]
    assert page.unchanged_periods == 1
    assert page.derived[0].key == KEY and page.derived[0].latest_value_display == "0,3"
    assert page.cross_checks and page.cross_checks[0].source_title == "Eurostat"
    assert page.cross_checks[0].value_display == "5,65"


def test_series_page_refuses_cross_check_and_withheld(page_db):
    assert reads.series_page(page_db, "s2") is None
    assert reads.series_page(page_db, "s3") is None
    assert reads.series_page(page_db, "nope") is None


def test_series_page_window_keeps_the_latest_years(page_db):
    page = reads.series_page(page_db, "s1", window="10")
    assert page.window == "10"
    assert [p["period"] for p in page.chart_points] == ["2026-01", "2026-02"]


def test_derived_page_shows_formula_inputs_and_attribution(page_db):
    page = reads.derived_page(page_db, KEY)
    assert page.title.startswith("População residente")
    assert "Variação homóloga" in page.formula_text
    assert page.unit_text == "%"
    assert [i.value_display for i in page.inputs] == ["5,7", "5,9"]
    assert page.base_id == "s1" and "População residente" in page.base_title
    assert page.attribution == "Fonte: INE - Calculado pelo Prumo"
    assert page.computed_text == "03/11/2026, 00:00 UTC"
    assert reads.derived_page(page_db, "nope") is None


def test_theme_page_groups_filters_and_paginates(page_db):
    page = reads.theme(page_db, "economy")
    assert page.total == 1 and page.groups[0].title == "População residente"
    assert page.groups[0].rows[0].value_display == "5,7"
    assert reads.theme(page_db, "economy", group="world").total == 0
    assert reads.theme(page_db, "economy", source="ine").total == 1
    assert reads.theme(page_db, "nope") is None


def test_search_is_accent_insensitive_and_capped(page_db):
    assert reads.search(page_db, "populacao")[0].id == "s1"
    assert reads.search(page_db, "POPULAÇÃO")[0].id == "s1"
    assert reads.search(page_db, "s1")[0].id == "s1"
    assert reads.search(page_db, "ine")[0].id == "s1"
    assert reads.search(page_db, "   ") == ()


def test_home_uses_the_curated_list_and_real_text(page_db, monkeypatch):
    monkeypatch.setattr(pt, "CURATED_HOME", [{"series": "s1", "label": "População",
                                              "derived": KEY}])
    page = reads.home(page_db)
    assert page.series_count == 1 and page.source_count == 1
    assert page.last_update_text.endswith("UTC")
    assert len(page.cards) == 1
    card = page.cards[0]
    assert card.label == "População" and card.value_display == "5,7"
    assert card.unit_text == "%" and card.period_text == "fevereiro de 2026"
    assert card.source_title == "INE - Instituto Nacional de Estatística"
    assert card.fetched_text == "03/11/2026"
    assert card.derived_value_display == "0,3" and card.derived_unit_text == "%"
    assert [t.code for t in page.themes] == ["economy", "demography", "energy"]
    assert page.sources == ("INE - Instituto Nacional de Estatística",)


def test_home_skips_a_curated_series_that_is_not_served(page_db, monkeypatch):
    monkeypatch.setattr(pt, "CURATED_HOME", [{"series": "s3", "label": "Fechada",
                                              "derived": None}])
    assert reads.home(page_db).cards == ()


def test_sources_page_separates_published_from_withheld(page_db):
    page = reads.sources_page(page_db)
    names = [s.name for s in page.published]
    assert "ine" in names and "eurostat" in names
    ine = next(s for s in page.published if s.name == "ine")
    assert ine.series == 1 and ine.last_fetched_text
    withheld = [s.name for s in page.withheld]
    assert withheld == ["ren"]
    assert page.withheld[0].series == 0


def test_fifteen_minute_page_opens_on_a_day_that_can_draw_a_line(db):
    """The newest day of a 15-minute series is usually partial; the page opens on the newest
    day with more than one interval, and an explicit day is still honoured."""
    from tests.ingest.fakes import spec
    reads.clear_cache()
    eredes = SourceSpec(name="eredes", licence="CC BY 4.0",
                        licence_url="https://www.e-redes.pt/termos", attribution="Fonte: E-REDES",
                        redistribution_ok=True)
    series = spec("e15", frequency="PT15M").model_copy(update={
        "source": eredes, "indicator_key": "eredes_production_market.PT.PT15M",
        "unit": "kWh", "geography": "PT", "theme": "energy"})
    sync_registry(db, [series])
    run = db.begin_run("eredes", "k15", T3)
    fid = db.record_raw_fetch(source_name="eredes", run_id=run, url="https://e-redes/x",
                              params_json=None, fetched_at=T3, http_status=200,
                              sha256="sha-15", path="p", n_bytes=10, ok=True)
    rows = [(Observation.from_raw("e15", f"2026-11-02T{h}:00:00+00:00", "100.0"), fid, T3)
            for h in ("00", "15")]
    rows.append((Observation.from_raw("e15", "2026-11-03T00:00:00+00:00", "90.0"), fid, T3))
    db.write_observations(run, rows)
    db.set_run_state(run, "verified")

    page = reads.series_page(db, "e15")
    assert page is not None and page.is_15m
    assert page.day == "2026-11-02" and len(page.chart_points) == 2
    assert page.days == ("2026-11-03", "2026-11-02")
    partial = reads.series_page(db, "e15", day="2026-11-03")
    assert partial.day == "2026-11-03" and len(partial.chart_points) == 1
