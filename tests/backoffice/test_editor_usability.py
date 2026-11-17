"""Focused usability contract for the CMS editor after the density refinement.

These three tests cover the visual contract that must survive the refinement:
a single compact status, native collapsible blocks, a top save toolbar, and every
form field name and value the save route already expects.
"""
import re
from collections import Counter
from pathlib import Path

import pytest

from tests.backoffice.test_cms_routes import ORIGIN, Env, page_create, page_form

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(tmp_path):
    return Env(tmp_path).client()


def _draft_form(html):
    match = re.search(
        r'<form method="post" action="[^"]*/save" data-dirty-watch.*?</form>',
        html, re.S,
    )
    assert match is not None
    return match.group(0)


def test_header_is_one_status_and_the_save_action_sits_above_the_work(client):
    assert page_create(client).status_code == 303
    response = client.get("/cms/page/precos")
    assert response.status_code == 200
    html = response.text

    header = re.search(r'<header class="page-head editor-head">.*?</header>', html, re.S)
    assert header is not None
    header = header.group(0)
    assert "eyebrow" not in header
    assert "page-sub" not in header
    assert "head-badges" not in header
    assert header.count('class="editor-status"') == 1
    assert "page/precos" in header
    assert "Versão 1" in header
    assert "Só rascunho, ainda não publicado" in header
    assert "Pré-visualizar rascunho" in header
    assert "Páginas e gráficos" not in header

    h1 = re.search(r'<h1 class="editor-title">(.*?)</h1>', html, re.S)
    assert h1 is not None and "Preços no consumidor" in h1.group(1)
    assert "page/precos" not in h1.group(1)

    assert 'class="section-nav editor-jumps"' in html
    assert 'role="tab"' not in html
    assert len(re.findall(r'<a href="#(?:rascunho|publicacao|historico|auditoria)"',
                          html)) == 4

    form = _draft_form(html)
    assert form.index('class="draft-toolbar"') < form.index('class="identity-card"')
    assert form.count('id="draft-note"') == 1
    assert form.count('name="note"') == 1
    toolbar = re.search(r'<div class="draft-toolbar">.*?</div>\s*</div>', form, re.S)
    assert toolbar is not None
    assert 'name="op" value="save"' in toolbar.group(0)
    assert "Guardar rascunho" in toolbar.group(0)
    assert 'for="draft-note"' in toolbar.group(0)


def test_blocks_are_native_disclosures_with_the_first_open_and_readable_labels(client):
    assert page_create(client).status_code == 303
    blocks = [
        {"type": "hero", "title": "Estatísticas oficiais"},
        {"type": "text", "text": "Primeiro parágrafo."},
        {"type": "heading", "title": "Secção seguinte"},
    ]
    assert client.post("/cms/page/precos/save", data=page_form(1, blocks=blocks),
                       headers=ORIGIN).status_code == 303
    html = client.get("/cms/page/precos").text
    form = _draft_form(html)

    found = re.findall(
        r'<details class="block-card" data-block data-block-type="([^"]+)"([^>]*)>',
        form,
    )
    assert [kind for kind, _ in found] == ["hero", "text", "heading"]
    assert " open" in found[0][1]
    assert all(" open" not in attrs for _, attrs in found[1:])

    summaries = re.findall(r'<summary class="block-summary">(.*?)</summary>', form, re.S)
    assert len(summaries) == 4  # three blocks plus the add form
    assert "Cabeçalho de abertura" in summaries[0]
    assert "Texto" in summaries[1]
    assert "Título de secção" in summaries[2]
    assert "Adicionar bloco" in summaries[3]
    assert ">HERO<" not in form and ">hero<" not in form

    for index in range(3):
        assert f'name="block_type_{index}"' in form
    assert form.index('class="draft-toolbar"') < form.index('class="block-card"')
    assert form.count('class="card-body"') == 5  # identity, three blocks, add form
    assert 'id="adicionar-bloco"' in form
    assert "Adicionar bloco" in form

    for tag in re.findall(r'<(?:input|select|textarea)\b[^>]*>', form):
        if 'name="block_' in tag:
            assert "disabled" not in tag

    # A normal page keeps identity visible; the reserved home identity is metadata,
    # so it starts collapsed while its first hero block stays open.
    normal_identity = re.search(r'<details class="identity-card"([^>]*)>', form)
    assert normal_identity is not None and " open" in normal_identity.group(1)

    assert client.post("/cms/home/prepare", data={"note": "preparar a página inicial"},
                       headers=ORIGIN).status_code == 303
    home = client.get("/cms/page/inicio").text
    home_form = _draft_form(home)
    home_identity = re.search(r'<details class="identity-card"([^>]*)>', home_form)
    assert home_identity is not None and " open" not in home_identity.group(1)
    first_block = re.search(
        r'<details class="block-card" data-block data-block-type="([^"]+)"([^>]*)>',
        home_form,
    )
    assert first_block is not None
    assert first_block.group(1) == "hero" and " open" in first_block.group(2)


def test_save_form_contract_is_preserved_without_duplicate_field_names(client):
    assert page_create(client).status_code == 303
    hero = {
        "type": "hero",
        "title": "Estatísticas oficiais",
        "eyebrow": "Dados",
        "note": "Nota do hero.",
        "counts": True,
        "freshness": True,
        "actions": [{"label": "Explorar", "href": "/temas"}],
    }
    assert client.post("/cms/page/precos/save", data=page_form(1, blocks=[hero]),
                       headers=ORIGIN).status_code == 303
    form = _draft_form(client.get("/cms/page/precos").text)

    fields = re.findall(r'<(?:input|select|textarea)\b[^>]*\bname="([^"]+)"', form)
    duplicates = {name: count for name, count in Counter(fields).items() if count > 1}
    assert duplicates == {}
    assert fields.count("note") == 1
    assert fields.count("version") == 1
    assert fields.count("block_count") == 1
    assert 'name="version" value="2"' in form
    assert 'name="block_count" value="1"' in form

    expected = {
        "version", "title", "introduction", "section", "block_count", "note",
        "block_type_0", "block_text_0", "block_title_0", "block_note_0",
        "block_eyebrow_0", "block_counts_0", "block_freshness_0",
        "block_link_label_0_0", "block_link_href_0_0",
        "block_link_label_0", "block_link_href_0",
        "block_series_0", "block_label_0", "block_derived_0", "block_chart_0",
        "add_type", "add_text", "add_title", "add_eyebrow", "add_series", "add_chart",
    }
    assert expected <= set(fields)
    for action in ("move_up_0", "move_down_0", "remove_0", "op"):
        assert f'name="{action}"' in form
    assert 'value="Estatísticas oficiais"' in form
    assert 'value="Dados"' in form
    assert 'value="Explorar"' in form
    assert 'value="/temas"' in form

    assert client.post("/cms/page/precos/save", data=page_form(2, blocks=[hero]),
                       headers=ORIGIN).status_code == 303
    saved = client.get("/cms/page/precos").text
    assert "Estatísticas oficiais" in saved
    assert 'name="block_count" value="1"' in saved


def test_saved_state_actions_carry_the_dirty_watch_contract(client):
    assert page_create(client).status_code == 303
    assert client.post("/cms/page/precos/save",
                       data=page_form(1, blocks=[{"type": "text", "text": "Original."}]),
                       headers=ORIGIN).status_code == 303
    assert client.post("/cms/page/precos/publish",
                       data={"version": "2", "note": "publicar"},
                       headers=ORIGIN).status_code == 303
    assert client.post("/cms/page/precos/save",
                       data=page_form(3, blocks=[{"type": "text", "text": "Novo."}]),
                       headers=ORIGIN).status_code == 303
    html = client.get("/cms/page/precos").text

    for action in ("publish", "unpublish", "restore", "duplicate"):
        forms = re.findall(
            rf'<form method="post" action="[^"]*/{action}"[^>]*>', html)
        assert forms, action
        assert all("data-requires-clean" in form for form in forms), action

    assert 'data-confirm="Publicar o rascunho guardado e substituir a versão em direto?"' in html
    assert "ainda não guardadas não são incluídas" in html
    assert "<noscript>" in html
    assert "publica apenas o rascunho guardado" in html
    assert "pré-visualize o rascunho guardado" in html

    js = (ROOT / "static/js/admin.js").read_text(encoding="utf-8")
    assert 'contains("select-filter")' in js              # the option filter is not a draft edit
    assert 'form[data-requires-clean]' in js
    assert "stopImmediatePropagation" in js                # no confirm before the dirty guard
    assert ".draft-save" in js and "save.focus()" in js
    assert "guarde o rascunho antes de publicar" in js
