"""CMS is the sole author of editorial comparisons; the public side only reads publication."""
import json
import re
from html import unescape

import pytest

from app import cms_comparisons, cms_reads
from backoffice.cms import Cms, CmsRefused
from backoffice.comparison_import import ComparisonImport, definitions, install
from ingest.db import open_db, read_db_readonly
from tests.app.conftest import HICP, UNEMP


def body(**changes):
    result = {"title": "Inflação e desemprego", "note": "Uma leitura editável pelo operador.",
              "series_a": HICP, "series_b": UNEMP, "series_extra": [], "axes": [0, 0],
              "window": "max", "scale": "single", "comparison_group": "portugal"}
    result.update(changes)
    return result


def payload(html):
    match = re.search(r'<script type="application/json" class="chart-data">(.*?)</script>',
                      html, re.S)
    assert match
    return json.loads(unescape(match[1]))


@pytest.fixture
def cms(site_path):
    return Cms(site_path, site_path)


def publish(cms, slug="real", **changes):
    meta = cms.create("chart", slug, body(**changes), actor="owner", note="criar comparativo")
    return cms.publish("chart", slug, meta["version"], actor="owner", note="publicar")


def test_no_code_catalogue_is_published_without_cms_content(client):
    response = client.get("/comparar")
    assert response.status_code == 200
    assert "Ainda não há comparações publicadas" in response.text
    assert "chart-data" not in response.text
    assert client.get("/comparar/inflacao-e-desemprego").status_code == 404
    assert client.get("/comparar/paises/eletricidade-domestica").status_code == 404


def test_draft_edits_do_not_change_public_content_and_publish_does(client, cms):
    meta = publish(cms)
    first = client.get("/comparar/real")
    assert first.status_code == 200
    before = payload(first.text)
    assert "Inflação e desemprego" in client.get("/comparar").text
    assert "authored-workspace" in first.text
    assert "notebook-chart-form" not in first.text
    assert 'name="series_a"' not in first.text
    assert 'name="escala"' not in first.text
    assert "Configurar" not in first.text
    assert "Acrescentar" not in first.text
    assert "/caderno?" not in first.text
    assert first.text.count("<h1") == 1
    meta = cms.save("chart", "real", meta["version"], body(
        title="Título alterado no backoffice", series_a=UNEMP, series_b=HICP),
        actor="owner", note="trocar ordem e título")
    assert payload(client.get("/comparar/real").text) == before
    assert "Título alterado no backoffice" not in client.get("/comparar").text
    cms.publish("chart", "real", meta["version"], actor="owner", note="publicar alteração")
    assert "Título alterado no backoffice" in client.get("/comparar").text
    assert payload(client.get("/comparar/real").text) != before


def test_public_query_cannot_override_authored_series_axes_or_window(client, cms):
    publish(cms)
    original = payload(client.get("/comparar/real").text)
    response = client.get("/comparar/real?s=worldbank.gdp_per_capita.PT&escala=dupla&janela=1a")
    assert response.status_code == 200
    assert payload(response.text) == original


def test_unpublish_does_not_resurrect_builtin_and_restore_is_private(client, cms):
    slug = "inflacao-e-desemprego"
    meta = publish(cms, slug)
    original_revision = meta["published_revision_id"]
    meta = cms.unpublish("chart", slug, meta["version"], actor="owner", note="retirar")
    assert client.get(f"/comparar/{slug}").status_code == 404
    assert slug not in client.get("/comparar").text
    cms.restore("chart", slug, meta["version"], original_revision, actor="owner", note="rever")
    assert client.get(f"/comparar/{slug}").status_code == 404


def test_library_chart_is_reusable_but_not_a_comparison(client, cms):
    publish(cms, comparison_group=None)
    assert client.get("/graficos/real").status_code == 200
    assert client.get("/comparar/real").status_code == 404
    assert 'href="/comparar/real"' not in client.get("/comparar").text


def test_withheld_selected_side_hides_entire_comparison(client, cms, site_path):
    publish(cms)
    db = open_db(site_path)
    try:
        db.conn.execute("UPDATE source SET redistribution_ok=0 WHERE name='ine'")
    finally:
        db.close()
    assert client.get("/comparar/real").status_code == 404
    assert 'href="/comparar/real"' not in client.get("/comparar").text


def test_country_legacy_address_redirects_only_to_published_cms(client, cms):
    publish(cms, comparison_group="countries", series_b=None, axes=[0])
    response = client.get("/comparar/paises/real", headers={"X-Forwarded-Prefix": "/dados"},
                          follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "/dados/comparar/real"
    assert client.get("/comparar/paises/unknown").status_code == 404


def test_index_and_detail_are_prefix_safe_and_public_get_only(client, cms):
    publish(cms)
    index = client.get("/comparar", headers={"X-Forwarded-Prefix": "/dados"})
    assert 'href="/dados/comparar/real"' in index.text
    assert "script-src 'self'" not in index.headers["content-security-policy"]
    detail = client.get("/comparar/real", headers={"X-Forwarded-Prefix": "/dados"})
    assert 'href="/dados/series/' in detail.text
    assert 'src="/dados/static/js/prumo-charts' in detail.text
    assert "script-src 'self'" in detail.headers["content-security-policy"]
    assert client.head("/comparar/real").status_code == 200
    assert client.post("/comparar/real", data={"title": "changed"}).status_code == 405


def test_importer_populates_real_documents_and_preserves_edits_on_rerun(cms, site_path):
    entries = (ComparisonImport("inflacao-e-desemprego", body()),)
    result = install(cms, actor="operator", note="converter catálogo autorizado", publish=True,
                     entries=entries)
    assert result[0]["status"] == "published"
    doc = cms.get("chart", entries[0].slug)
    assert doc["published"].series_ids == (HICP, UNEMP)
    assert len(doc["events"]) == 2
    meta = cms.save("chart", entries[0].slug, doc["meta"]["version"], body(title="Texto do João"),
                    actor="owner", note="personalizar")
    again = install(cms, actor="operator", note="repetir sem substituir", publish=True,
                    entries=entries)
    assert again[0]["status"] == "preserved"
    assert cms.get("chart", entries[0].slug)["draft"].title == "Texto do João"
    assert cms.get("chart", entries[0].slug)["meta"]["version"] == meta["version"]
    index = read_db_readonly(site_path, cms_comparisons.index)
    assert index.groups[0].rows[0].title == "Inflação e desemprego"


def test_importer_refuses_any_existing_private_draft_before_writing(cms):
    cms.create("chart", "second", body(), actor="owner", note="trabalho do João")
    with pytest.raises(CmsRefused, match="rascunho"):
        install(cms, actor="operator", note="importar", publish=True, entries=(
            ComparisonImport("first", body()), ComparisonImport("second", body())))
    assert cms.get("chart", "first") is None


def test_import_material_covers_all_existing_real_comparisons():
    entries = definitions()
    assert len(entries) == 9
    assert {entry.slug for entry in entries} == {
        "inflacao-e-desemprego", "euribor-e-inflacao", "credito-e-taxa",
        "taxas-juro-credito-depositos", "divida-saldo-pib-per-capita",
        "comercio-externo-pib-per-capita", "eletricidade-domestica", "pib-por-habitante",
        "divida-publica"}
    assert {entry.body["comparison_group"] for entry in entries} == {"portugal", "countries"}
    for entry in entries:
        assert "teste" not in entry.slug
        assert len(entry.body["note"]) > 80


def test_directory_never_prepares_each_full_chart(client, cms, monkeypatch):
    publish(cms)
    def refuse_draw(*args, **kwargs):
        raise AssertionError("directory must not prepare chart geometry or history")
    monkeypatch.setattr(cms_reads, "chart_view", refuse_draw)
    response = client.get("/comparar")
    assert response.status_code == 200
    assert 'href="/comparar/real"' in response.text


def test_preview_uses_same_svg_without_executable_bundle(cms, site_path):
    publish(cms)
    template, draft = cms.preview("chart", "real")
    public = read_db_readonly(site_path, lambda db: cms_reads.public_chart(db, "real"))
    assert template == "cms_chart.html"
    assert public is not None
    assert draft.chart == public.chart
