"""CMS service: the contract the backoffice editor codes against.

Focused on what can go wrong in an authored workflow: stale forms, drafts leaking public,
publication refusing ineligible references atomically, revision history, chart usages, and the
guarantee that no CMS action changes source or observation data.
"""
import hashlib

import pytest

from app import cms_reads
from backoffice.cms import Cms, CmsConflict, CmsRefused, CmsUnavailable
from ingest import cms as documents
from ingest.db import Db, open_db, open_db_for_write, read_db_readonly
from presentation.catalog import pt
from tests.app.conftest import (
    DERIVED,
    HICP,
    INACTIVE,
    T1,
    T2,
    UNEMP,
    WITHHELD,
    WORLD,
    build,
    fetch,
)


def _page(blocks=None, *, title="Preços", introduction="Introdução.", section="economy"):
    return {"title": title, "introduction": introduction, "section": section,
            "blocks": blocks if blocks is not None else [{"type": "text", "text": "Texto."}]}


def _chart(**overrides):
    data = {"title": "Inflação", "note": "Nota.", "series_a": HICP, "series_b": None,
            "derived_key": None, "window": "max", "scale": "single", "day": None}
    data.update(overrides)
    return data


@pytest.fixture
def env(tmp_path):
    path = tmp_path / "prumo.db"
    build(path)
    return Cms(path, path), path


def add_series(path, series_id, *, key, frequency="M", unit="%", theme="economy",
               geography="PT", source="ine"):
    db = open_db(path)
    try:
        db.conn.execute(
            "INSERT INTO series(id, source_id, indicator_key, role, theme, geography, "
            "frequency, unit, active) SELECT ?, id, ?, 'primary', ?, ?, ?, ?, 1 "
            "FROM source WHERE name = ?",
            (series_id, key, theme, geography, frequency, unit, source))
    finally:
        db.close()


def public_page(path, slug):
    return read_db_readonly(path, lambda db: cms_reads.public_page(db, slug))


def public_chart(path, slug):
    return read_db_readonly(path, lambda db: cms_reads.public_chart(db, slug))


def fingerprint(path):
    """sha256 over the stored source/observation/quarantine/derived rows, order-stable."""
    digest = hashlib.sha256()
    db = open_db(path)
    try:
        for table in ("source", "series", "observation", "quarantine", "derived_series",
                      "derived_observation"):
            rows = db.conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            digest.update(table.encode())
            digest.update(repr(rows).encode())
    finally:
        db.close()
    return digest.hexdigest()


def published(cms, kind, slug, body, version):
    return cms.publish(kind, slug, version, actor="owner", note="publicar")


def test_create_get_list_preview_and_public_boundary(env):
    cms, path = env
    chart = cms.create("chart", "inflacao", _chart(), actor="owner", note="criar")
    published(cms, "chart", "inflacao", _chart(), chart["version"])
    page = cms.create("page", "precos", _page([
        {"type": "text", "text": "Um parágrafo."},
        {"type": "card", "series_id": HICP, "derived_key": None},
        {"type": "chart", "chart_slug": "inflacao"},
    ]), actor="owner", note="criar")

    got = cms.get("page", "precos")
    assert set(got) == {"meta", "draft", "published", "history", "events", "usages"}
    assert isinstance(got["draft"], documents.PageDocument)
    assert got["published"] is None
    assert len(got["history"]) == 1 and len(got["events"]) == 1
    assert got["usages"] == ()

    summaries = cms.list("page")
    assert summaries == ({"kind": "page", "slug": "precos", "title": "Preços", "version": 1,
                          "published": False, "section": "economy"},)
    assert cms.charts()[0]["slug"] == "inflacao"

    name, view = cms.preview("page", "precos")
    assert name == "cms_page.html"
    assert view.title == "Preços" and view.has_charts
    assert public_page(path, "precos") is None  # a draft never reaches a public read

    meta = published(cms, "page", "precos", _page([
        {"type": "text", "text": "Um parágrafo."},
        {"type": "card", "series_id": HICP, "derived_key": None},
        {"type": "chart", "chart_slug": "inflacao"},
    ]), page["version"])
    assert meta["published_revision_id"] is not None
    assert public_page(path, "precos").title == "Preços"
    assert public_chart(path, "inflacao").title == "Inflação"


def test_stale_save_writes_nothing_and_published_content_does_not_move(env):
    cms, path = env
    meta = cms.create("page", "precos", _page(), actor="owner", note="criar")
    saved = cms.save("page", "precos", meta["version"], _page(title="Primeira"),
                     actor="owner", note="editar")
    meta = published(cms, "page", "precos", _page(title="Primeira"), saved["version"])
    history_before = len(cms.get("page", "precos")["history"])
    with pytest.raises(CmsConflict):
        cms.save("page", "precos", meta["version"] - 1, _page(title="Stale"),
                 actor="owner", note="stale")
    assert cms.get("page", "precos")["meta"]["version"] == meta["version"]
    assert len(cms.get("page", "precos")["history"]) == history_before

    saved = cms.save("page", "precos", meta["version"], _page(title="Segunda"),
                     actor="owner", note="editar")
    assert saved["version"] == meta["version"] + 1
    assert cms.get("page", "precos")["draft"].title == "Segunda"
    assert public_page(path, "precos").title == "Primeira"   # live content unchanged
    assert cms.preview("page", "precos")[1].title == "Segunda"

    published(cms, "page", "precos", _page(title="Segunda"), saved["version"])
    assert public_page(path, "precos").title == "Segunda"


def test_publish_refuses_ineligible_cards_and_a_derived_base_change(env):
    cms, path = env
    for slug, series in (("retido", WITHHELD), ("inactivo", INACTIVE)):
        created = cms.create("page", slug, _page([
            {"type": "card", "series_id": series, "derived_key": None}]),
            actor="owner", note="criar")
        with pytest.raises(CmsRefused):
            published(cms, "page", slug, _page([
                {"type": "card", "series_id": series, "derived_key": None}]),
                created["version"])
        current = cms.get("page", slug)
        assert current["meta"]["published_revision_id"] is None
        assert current["meta"]["version"] == created["version"]
        assert [event["action"] for event in current["events"]] == ["created"]
        assert public_page(path, slug) is None

    created = cms.create("page", "base-trocada", _page([
        {"type": "card", "series_id": HICP, "derived_key": DERIVED}]),
        actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        published(cms, "page", "base-trocada", _page([
            {"type": "card", "series_id": HICP, "derived_key": DERIVED}]),
            created["version"])
    assert cms.get("page", "base-trocada")["meta"]["published_revision_id"] is None


def test_chart_publish_refuses_frequency_mix_mixed_units_and_a_missing_day(env):
    cms, path = env
    mixed = cms.create("chart", "frequencias", _chart(series_b=WORLD), actor="owner",
                       note="criar")
    with pytest.raises(CmsRefused):
        published(cms, "chart", "frequencias", _chart(series_b=WORLD), mixed["version"])
    assert cms.get("chart", "frequencias")["meta"]["published_revision_id"] is None

    add_series(path, "ine.units_eur.PT", key="credit_consumer.PT.M", unit="MEUR")
    add_series(path, "ine.units_pct.PT", key="credit_housing.PT.M", unit="%")
    db = open_db(path)
    try:
        fetch(db, "ine.units_eur.PT", {"2026-10": "10.0"}, T1)
        fetch(db, "ine.units_pct.PT", {"2026-10": "20.0"}, T2)
    finally:
        db.close()

    single = _chart(title="Unidades", series_a="ine.units_eur.PT",
                    series_b="ine.units_pct.PT", scale="single")
    meta = cms.create("chart", "unidades", single, actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        published(cms, "chart", "unidades", single, meta["version"])
    dual = {**single, "scale": "dual"}
    saved = cms.save("chart", "unidades", meta["version"], dual, actor="owner", note="editar")
    published(cms, "chart", "unidades", dual, saved["version"])
    assert public_chart(path, "unidades").is_pair

    add_series(path, "eredes.service_15m.PT", key="eredes_production_total.PT.PT15M",
               frequency="PT15M", unit="GWh", theme="energy")
    db = open_db(path)
    try:
        fetch(db, "eredes.service_15m.PT", {"2026-11-01T00:00:00+00:00": "1.0"}, T1)
    finally:
        db.close()
    no_day = _chart(title="Dia", series_a="eredes.service_15m.PT")
    meta = cms.create("chart", "dia", no_day, actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        published(cms, "chart", "dia", no_day, meta["version"])
    with_day = {**no_day, "day": "2026-11-01"}
    saved = cms.save("chart", "dia", meta["version"], with_day, actor="owner", note="editar")
    published(cms, "chart", "dia", with_day, saved["version"])
    assert public_chart(path, "dia").table[0].period_text.startswith("01/11/2026")


def test_missing_reader_text_excludes_the_series_and_refuses_publication(env, monkeypatch):
    cms, path = env
    monkeypatch.delitem(pt.FAMILIES, "hicp_yoy")
    assert all(choice["id"] != HICP for choice in cms.choices())
    created = cms.create("page", "sem-texto", _page([
        {"type": "card", "series_id": HICP, "derived_key": None}]),
        actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        published(cms, "page", "sem-texto", _page([
            {"type": "card", "series_id": HICP, "derived_key": None}]),
            created["version"])


def test_publication_check_is_inside_the_storage_transaction(env):
    cms, path = env
    meta = cms.create("page", "atomo", _page(), actor="owner", note="criar")
    db = open_db_for_write(path)
    try:
        with pytest.raises(CmsRefused):
            db.cms_publish("page", "atomo", meta["version"], actor="owner", note="verificar",
                           check=lambda kind, body: (_ for _ in ()).throw(
                               CmsRefused("referência recusada")))
        assert db.cms_get("page", "atomo")["version"] == meta["version"]
        assert db.cms_get("page", "atomo")["published_revision_id"] is None
    finally:
        db.close()
    assert public_page(path, "atomo") is None
    published(cms, "page", "atomo", _page(), meta["version"])
    assert public_page(path, "atomo") is not None


def test_restore_creates_a_new_draft_and_duplicate_a_new_slug(env):
    cms, path = env
    meta = cms.create("page", "precos", _page(title="Original"), actor="owner", note="criar")
    first_revision = meta["draft_revision_id"]
    meta = cms.save("page", "precos", meta["version"], _page(title="Editada"),
                    actor="owner", note="editar")
    meta = published(cms, "page", "precos", _page(title="Editada"), meta["version"])
    restored = cms.restore("page", "precos", meta["version"], first_revision,
                           actor="owner", note="recuperar")
    got = cms.get("page", "precos")
    assert got["draft"].title == "Original"
    assert got["published"].title == "Editada"
    assert got["meta"]["version"] == restored["version"]
    assert got["history"][0]["id"] != first_revision      # a new revision, not a rewrite
    assert public_page(path, "precos").title == "Editada"

    copy = cms.duplicate("page", "precos", "precos-copia", version=restored["version"],
                         actor="owner", note="duplicar")
    assert copy["slug"] == "precos-copia"
    assert cms.get("page", "precos-copia")["draft"].title == "Original"
    assert cms.get("page", "precos")["draft"].title == "Original"
    with pytest.raises(CmsRefused):
        cms.duplicate("page", "precos", "precos", version=restored["version"],
                      actor="owner", note="duplicar")


def test_chart_usages_show_draft_and_published_pages(env):
    cms, path = env
    meta = cms.create("chart", "inflacao", _chart(), actor="owner", note="criar")
    published(cms, "chart", "inflacao", _chart(), meta["version"])
    page = cms.create("page", "precos", _page(), actor="owner", note="criar")
    published(cms, "page", "precos", _page(), page["version"])
    draft = cms.save("page", "precos", page["version"] + 1, _page([
        {"type": "chart", "chart_slug": "inflacao"}]), actor="owner", note="editar rascunho")
    assert cms.get("chart", "inflacao")["usages"] == (
        {"kind": "page", "slug": "precos", "title": "Preços", "published": False},)
    published(cms, "page", "precos", _page([
        {"type": "chart", "chart_slug": "inflacao"}]), draft["version"])
    assert cms.get("chart", "inflacao")["usages"][0]["published"] is True
    cms.unpublish("page", "precos", draft["version"] + 1, actor="owner", note="retirar")
    assert cms.get("chart", "inflacao")["usages"][0]["published"] is False


def test_choices_are_eligible_and_carry_raw_and_reader_tokens(env):
    cms, _path = env
    choices = {choice["id"]: choice for choice in cms.choices()}
    assert HICP in choices and UNEMP in choices
    assert WITHHELD not in choices and INACTIVE not in choices and "eurostat.hicp_yoy.PT" not in choices
    hicp = choices[HICP]
    assert hicp["frequency"] == "M" and hicp["frequency_text"] == "Mensal"
    assert hicp["unit"] == "%" and hicp["unit_text"] == "%"
    assert hicp["geography"] == "PT" and hicp["geography_text"] == "Portugal"
    assert hicp["source"] == "ine" and hicp["source_title"].startswith("INE")
    assert hicp["derived"] == ()
    assert choices[UNEMP]["derived"] == (
        {"key": DERIVED, "title": pt.TITLES[DERIVED]},)


def test_choices_carry_the_served_period_range_and_an_optional_label(env):
    cms, path = env
    add_series(path, "ine.meur_test.PT", key="credit_consumer.PT.M", unit="MEUR")
    db = open_db(path)
    try:
        fetch(db, "ine.meur_test.PT", {"2025-01": "10.0", "2026-10": "12.0"}, T1)
    finally:
        db.close()
    choices = {choice["id"]: choice for choice in cms.choices()}
    hicp = choices[HICP]
    assert (hicp["first_period"], hicp["latest_period"]) == ("2026-08", "2026-10")
    assert hicp["coverage_text"] == "agosto de 2026 a outubro de 2026"
    assert hicp["option_label"] == (
        "Taxa de variação homóloga do IHPC - Portugal | agosto de 2026 a outubro de 2026"
        " | % | Mensal | Portugal | INE - Instituto Nacional de Estatística")
    meur = choices["ine.meur_test.PT"]
    assert meur["unit_text"] == "milhões de euros"
    assert meur["coverage_text"] == "janeiro de 2025 a outubro de 2026"
    assert "| MEUR |" in meur["option_label"]
    assert "milhões de euros" not in meur["option_label"]


def test_choices_never_load_a_series_history(env, monkeypatch):
    cms, _path = env

    def boom(*_args, **_kwargs):
        raise AssertionError("choices must not materialise a series history")

    monkeypatch.setattr(Db, "public_series_values", boom)
    monkeypatch.setattr(Db, "public_recent_values", boom)
    assert {choice["id"] for choice in cms.choices()} >= {HICP, UNEMP}


def test_stale_duplicate_conflicts_and_creates_nothing(env):
    cms, _path = env
    meta = cms.create("page", "precos", _page(), actor="owner", note="criar")
    meta = cms.save("page", "precos", meta["version"], _page(title="Segunda"),
                    actor="owner", note="editar")
    before = _document_state(cms, "page", "precos")
    with pytest.raises(CmsConflict) as exc:
        cms.duplicate("page", "precos", "copia", version=meta["version"] - 1,
                      actor="owner", note="duplicar")
    assert exc.value.expected == meta["version"] - 1 and exc.value.actual == meta["version"]
    assert _document_state(cms, "page", "precos") == before
    assert cms.get("page", "copia") is None
    assert [summary["slug"] for summary in cms.list("page")] == ["precos"]


def _page_with_chart(cms, chart_slug="inflacao"):
    meta = cms.create("chart", chart_slug, _chart(), actor="owner", note="criar")
    published(cms, "chart", chart_slug, _chart(), meta["version"])
    blocks = [{"type": "chart", "chart_slug": chart_slug}]
    page = cms.create("page", "precos", _page(blocks), actor="owner", note="criar")
    published(cms, "page", "precos", _page(blocks), page["version"])


def _document_state(cms, kind, slug):
    got = cms.get(kind, slug)
    return (got["meta"]["version"], got["meta"]["published_revision_id"],
            len(got["history"]), len(got["events"]))


def _refused_page_republish(cms, path):
    """Save an identical draft after the data changed, then prove publish writes nothing."""
    blocks = [{"type": "chart", "chart_slug": "inflacao"}]
    meta = cms.get("page", "precos")["meta"]
    saved = cms.save("page", "precos", meta["version"], _page(blocks), actor="owner",
                     note="novo rascunho")
    before = _document_state(cms, "page", "precos")
    live = cms.get("page", "precos")["published"]
    with pytest.raises(CmsRefused):
        cms.publish("page", "precos", saved["version"], actor="owner", note="publicar")
    assert _document_state(cms, "page", "precos") == before
    assert cms.get("page", "precos")["published"].title == live.title
    public = public_page(path, "precos")
    assert public is not None and public.availability_note


def test_page_publish_refuses_a_chart_whose_licence_was_revoked_after_publication(env):
    cms, path = env
    _page_with_chart(cms)
    db = open_db(path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok = 0 WHERE name = 'ine'")
    finally:
        db.close()
    _refused_page_republish(cms, path)


def test_page_publish_refuses_a_chart_whose_run_was_withdrawn(env):
    cms, path = env
    _page_with_chart(cms)
    db = open_db(path)
    try:
        runs = [row[0] for row in db.conn.execute(
            "SELECT DISTINCT dataset_run_id FROM observation WHERE series_id = ?", (HICP,))]
        for run_id in runs:
            db.withdraw_run(run_id, "correção do publicador", T2)
    finally:
        db.close()
    _refused_page_republish(cms, path)


def test_page_publish_refuses_a_chart_whose_reader_text_disappeared(env, monkeypatch):
    cms, path = env
    _page_with_chart(cms)
    monkeypatch.delitem(pt.FAMILIES, "hicp_yoy")
    _refused_page_republish(cms, path)


def test_page_publish_refuses_a_chart_with_only_non_finite_values(env):
    cms, path = env
    add_series(path, "ine.nan_test.PT", key="consumer_confidence.PT.M", unit="%")
    db = open_db(path)
    try:
        fetch(db, "ine.nan_test.PT", {"2026-10": "50.0"}, T1)
    finally:
        db.close()
    chart = _chart(series_a="ine.nan_test.PT")
    meta = cms.create("chart", "inflacao", chart, actor="owner", note="criar")
    published(cms, "chart", "inflacao", chart, meta["version"])
    blocks = [{"type": "chart", "chart_slug": "inflacao"}]
    page = cms.create("page", "precos", _page(blocks), actor="owner", note="criar")
    published(cms, "page", "precos", _page(blocks), page["version"])
    db = open_db(path)
    try:
        db.conn.execute("UPDATE observation SET value_text = 'NaN', value = 1.0 "
                        "WHERE series_id = 'ine.nan_test.PT'")
    finally:
        db.close()
    assert public_chart(path, "inflacao") is None
    _refused_page_republish(cms, path)


def test_invalid_shapes_and_slugs_are_refused_not_raised(env):
    cms, _path = env
    with pytest.raises(CmsRefused):
        cms.create("page", "Mau-Slug", _page(), actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        cms.create("page", "bom", _page(title=f"Título {chr(0x2014)} com travessão"),
                   actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        cms.create("page", "bom", {**_page(), "extra": True}, actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        cms.list("unknown")
    meta = cms.create("page", "bom", _page(), actor="owner", note="criar")
    with pytest.raises(CmsRefused):
        cms.save("page", "bom", meta["version"], {"title": "x"}, actor="owner", note="editar")
    assert cms.get("page", "nunca-existiu") is None


def test_an_unavailable_writable_mount_never_blocks_reading_preview(env):
    cms, path = env
    ro = Cms(path, None)
    assert ro.available() is False
    with pytest.raises(CmsUnavailable):
        ro.create("page", "precos", _page(), actor="owner", note="criar")
    assert ro.preview("page", "precos") is None


def test_cms_lifecycle_does_not_change_source_or_observation_fingerprints(env):
    cms, path = env
    before = fingerprint(path)
    chart = cms.create("chart", "inflacao", _chart(), actor="owner", note="criar")
    chart = cms.publish("chart", "inflacao", chart["version"], actor="owner", note="publicar")
    page = cms.create("page", "precos", _page([
        {"type": "card", "series_id": HICP, "derived_key": None},
        {"type": "chart", "chart_slug": "inflacao"}]), actor="owner", note="criar")
    page_first = page["draft_revision_id"]
    page = cms.publish("page", "precos", page["version"], actor="owner", note="publicar")
    page = cms.save("page", "precos", page["version"], _page(title="Editada"),
                    actor="owner", note="editar")
    cms.restore("page", "precos", page["version"], page_first, actor="owner", note="recuperar")
    current = cms.get("page", "precos")["meta"]["version"]
    cms.duplicate("page", "precos", "precos-copia", version=current, actor="owner",
                  note="duplicar")
    chart_version = cms.get("chart", "inflacao")["meta"]["version"]
    cms.unpublish("chart", "inflacao", chart_version, actor="owner", note="retirar")
    assert fingerprint(path) == before
