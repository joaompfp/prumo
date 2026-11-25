"""The shared card's optional notebook entry, and the CMS cards that use it.

The legacy card contract stays byte-for-byte when no caller supplies
`card_create_path`. Only `_cms_blocks.html` supplies it, so a CMS indicator card can
start a one-indicator notebook without changing the authored text, the legacy home,
or the notebook cards that already carry their own remove control.
"""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from app import reads
from app.cms_reads import HOME_SLUG
from app.main import create_app
from backoffice.cms import Cms
from tests.app.conftest import HICP, UNEMP

TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"
TITLE = "Taxa de variação homóloga do IHPC - Portugal"
CREATE_LABEL = f"Criar caderno para {TITLE}"

EXPECTED_LEGACY_CARD = (
    '<article class="card">\n'
    '      <p class="card-label">Inflação (IHPC)</p>\n'
    '      <p class="card-value">1,8 <span class="card-unit">%</span></p>\n'
    '      <p class="card-period">out 2026</p>\n'
    '      <p class="card-tags"></p>\n'
    '      <p class="calc-line"></p>\n'
    '      <div class="card-spark"><svg class="spark" aria-hidden="true"></svg></div>\n'
    '      <p class="card-source">INE - Instituto Nacional de Estatística · recolhido a '
    '03/11/2026, 09:00 UTC</p>\n'
    '      <a class="card-link" href="/series/ine.hicp_yoy.PT">Série e proveniência</a>\n'
    '    </article>'
)


def _card() -> SimpleNamespace:
    return SimpleNamespace(
        series_id=HICP, href=f"/series/{HICP}", label="Inflação (IHPC)", title=TITLE,
        value_display="1,8", unit_text="%", period_text="out 2026",
        source_title="INE - Instituto Nacional de Estatística",
        fetched_text="03/11/2026, 09:00 UTC", status_text="", derived_title=None,
        derived_label=None, derived_value_display=None, derived_unit_text=None,
        derived_period_text=None, spark_points=())


def _render_card(**overrides) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    env.globals["spark"] = lambda points: Markup('<svg class="spark" aria-hidden="true"></svg>')
    env.globals["notebook_copy"] = SimpleNamespace(remove_label="Remover do caderno")
    context = {"card": _card(), "base": "", **overrides}
    return env.get_template("_card.html").render(**context)


def _publish_home_with_card(site_path, series_ids=(HICP,)) -> None:
    cms = Cms(site_path, site_path)
    meta = cms.prepare_home(actor="owner", note="preparar a página inicial")
    blocks = [{"type": "heading", "title": "Destaques"}]
    blocks.extend({"type": "card", "series_id": series_id, "derived_key": None}
                  for series_id in series_ids)
    saved = cms.save("page", HOME_SLUG, meta["version"], {
        "title": "Início", "introduction": "", "section": "general", "blocks": blocks,
    }, actor="owner", note="cartão em destaque")
    cms.publish("page", HOME_SLUG, saved["version"], actor="owner", note="publicar")
    reads.clear_cache()


def test_shared_card_without_the_optional_entry_keeps_the_legacy_bytes():
    assert _render_card() == EXPECTED_LEGACY_CARD
    assert "Criar caderno" not in _render_card()
    assert 'class="card-actions"' not in _render_card()


def test_shared_card_adds_one_entry_only_when_the_caller_supplies_a_path():
    html = _render_card(card_create_path=f"/caderno?s={HICP}")
    assert (
        f'<p class="card-actions"><a class="card-link" href="/series/{HICP}">'
        'Série e proveniência</a> '
        f'<a class="card-create" href="/caderno?s={HICP}" aria-label="{CREATE_LABEL}">'
        'Criar caderno</a></p>'
    ) in html
    assert html.count('class="card-create"') == 1


def test_legacy_home_card_does_not_gain_the_cms_notebook_entry(client):
    html = client.get("/").text
    assert 'class="card-create"' not in html
    assert "Criar caderno" not in html


def test_cms_home_card_offers_and_opens_a_one_indicator_notebook(site_path):
    _publish_home_with_card(site_path)
    with TestClient(create_app(str(site_path))) as client:
        html = client.get("/").text
        assert html.count('class="card-create"') == 1
        assert f'href="/caderno?s={HICP}"' in html
        assert f'aria-label="{CREATE_LABEL}"' in html
        assert '>Criar caderno</a>' in html
        assert "estas duas séries" not in html
        assert "Adicionar ao caderno" not in html

        notebook = client.get(f"/caderno?s={HICP}")
        assert notebook.status_code == 200
        assert TITLE in notebook.text
        assert f'value="{HICP}"' in notebook.text
        assert 'class="card-create"' not in notebook.text
        assert "Criar caderno" not in notebook.text


def test_cms_card_entry_carries_the_public_mount(site_path):
    _publish_home_with_card(site_path)
    with TestClient(create_app(str(site_path))) as client:
        html = client.get("/", headers={"X-Forwarded-Prefix": "/dados"}).text
    assert f'href="/dados/caderno?s={HICP}"' in html
    assert f'aria-label="{CREATE_LABEL}"' in html


def test_each_cms_card_entry_names_only_its_own_indicator(site_path):
    _publish_home_with_card(site_path, series_ids=(HICP, UNEMP))
    with TestClient(create_app(str(site_path))) as client:
        html = client.get("/").text
    entries = re.findall(r'<a class="card-create" href="([^"]+)"[^>]*>Criar caderno</a>', html)
    assert entries == [f"/caderno?s={HICP}", f"/caderno?s={UNEMP}"]
    assert "&" not in "".join(entries)
    assert html.count('class="card-create"') == 2


def test_notebook_cards_keep_only_their_remove_control(client):
    html = client.get(f"/caderno?s={HICP}&s={UNEMP}").text
    assert 'class="card-create"' not in html
    assert "Criar caderno" not in html
    assert html.count('class="card-remove"') == 2


@pytest.mark.parametrize("prefix", ["", "/dados"])
def test_shared_card_does_not_duplicate_controls_when_a_remove_path_is_present(prefix):
    html = _render_card(card_remove_path=f"/caderno?s={HICP}", base=prefix)
    assert html.count('class="card-link"') == 1
    assert html.count('class="card-remove"') == 1
    assert 'class="card-create"' not in html
