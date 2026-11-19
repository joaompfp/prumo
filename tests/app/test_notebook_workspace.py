"""Focused contract for the notebook analytical workspace (roadmap A1-A2).

These tests read the real installed application response: the same route, templates, one
read-only snapshot and security middleware the reader gets. They pin the working composition
rather than a screenshot: chart first, its visible controls, the common period and per-side
source beside the plot, search before the cards, settings after the plot, honest per-card chart
state and a single native GET form. Visual acceptance remains a separate browser gate.
"""
import re
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from ingest.db import open_db
from ingest.registry import sync_registry
from tests.app.conftest import (
    HICP,
    INACTIVE,
    T1,
    T3,
    UNEMP,
    fetch,
    make_spec,
)

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "static" / "css" / "prumo.css"
FAMILIES = ("hicp_yoy", "unemployment_rate", "consumer_confidence", "credit_consumer",
            "credit_housing", "ipi_total", "euribor_3m")


def build_real_case(tmp_path):
    """The published HICP/unemployment shape: October card versus September common plot."""
    path = tmp_path / "workspace-real.db"
    db = open_db(path)
    try:
        sync_registry(db, [make_spec(HICP), make_spec(UNEMP, key="unemployment_rate.PT.M")])
        fetch(db, HICP, {"2026-08": "2.1", "2026-09": "2.0", "2026-10": "1.8"}, T1)
        fetch(db, UNEMP, {"2026-08": "6.4", "2026-09": "6.2"}, T3, flag="provisional")
    finally:
        db.close()
    return path


def client(path):
    return TestClient(create_app(str(path)))


def visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children = []
        self.text = ""

    def classes(self):
        return set(self.attrs.get("class", "").split())

    def find_all(self, tag=None, cls=None):
        found = []
        for child in self.children:
            if (tag is None or child.tag == tag) and (cls is None or cls in child.classes()):
                found.append(child)
            found.extend(child.find_all(tag, cls))
        return found

    def all_text(self):
        return " ".join([self.text, *(child.all_text() for child in self.children)])


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {name: value or "" for name, value in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, {name: value or "" for name, value in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_data(self, data):
        self.stack[-1].text += data

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return


def dom(html: str) -> Node:
    parser = _Parser()
    parser.feed(html)
    return parser.root


def notebook_html(site_path, query=f"?s={HICP}&s={UNEMP}") -> str:
    with client(site_path) as site:
        response = site.get(f"/caderno{query}")
    assert response.status_code == 200
    return response.text


def one(root, tag, cls=None):
    found = root.find_all(tag, cls)
    assert len(found) == 1, (tag, cls, len(found))
    return found[0]


def chart_form(root):
    forms = [node for node in root.find_all("form")
             if node.attrs.get("id") == "notebook-chart-form"]
    assert len(forms) == 1
    return forms[0]


def has_ancestor(node, ancestor):
    parent = node.parent
    while parent is not None:
        if parent is ancestor:
            return True
        parent = parent.parent
    return False


def has_form_ancestor(node):
    parent = node.parent
    while parent is not None:
        if parent.tag == "form":
            return True
        parent = parent.parent
    return False


def form_fields(form):
    """The successful controls a browser would submit from this native GET form."""
    fields = []
    for node in form.find_all("input"):
        kind = node.attrs.get("type", "text")
        if kind in {"submit", "button", "reset"}:
            continue
        if kind in {"checkbox", "radio"} and "checked" not in node.attrs:
            continue
        name = node.attrs.get("name")
        if name:
            fields.append((name, node.attrs.get("value", "")))
    for select in form.find_all("select"):
        options = select.find_all("option")
        assert options
        chosen = next((option for option in options if "selected" in option.attrs), options[0])
        fields.append((select.attrs["name"], chosen.attrs.get("value", "")))
    return fields


def submit_fields(site_path, fields, *, replace=None, drop=()):
    """Submit the form's own controls back to the installed route, as a browser would."""
    params = []
    for name, value in fields:
        if name in drop:
            continue
        if replace and name in replace:
            value = replace[name]
        if value is not None:
            params.append((name, value))
    with client(site_path) as site:
        response = site.get("/caderno", params=params)
    assert response.status_code == 200
    return response.text


def test_workspace_is_a_notebook_scoped_fluid_column_not_the_prose_wrap(site_path):
    html = notebook_html(site_path)
    root = dom(html)
    main = one(root, "main")
    assert "notebook-main" in main.classes()
    workspace = one(root, "div", "notebook-workspace")
    assert workspace.parent is main

    css = CSS.read_text(encoding="utf-8")
    assert ".wrap.notebook-main { max-width: none; }" in css
    assert ".notebook-workspace {" in css
    workspace_rule = css[css.index(".notebook-workspace {"):]
    workspace_rule = workspace_rule[:workspace_rule.index("}")]
    # The working width is bounded by the viewport height at the chart's own aspect ratio and
    # a readable wide-monitor cap, never by the 1240px prose measure.
    assert "min(100%" in workspace_rule
    assert "100vh" in workspace_rule
    assert "2400px" in workspace_rule
    assert "margin-inline: auto" in workspace_rule


def test_compact_title_keeps_functional_roles_at_the_approved_scale(site_path):
    html = notebook_html(site_path)
    root = dom(html)
    header = one(root, "header", "page-head")
    heading = one(header, "h1")
    assert heading.all_text().strip() == "Caderno de indicadores"
    status = one(header, "p", "meta")
    assert "2 de 12 séries." in status.all_text()
    # The long public-link and snapshot explanation moved below the work surface.
    assert "Qualquer pessoa com esta ligação" not in header.all_text()
    assert "não é um retrato histórico" not in header.all_text()

    css = CSS.read_text(encoding="utf-8")
    rule = css[css.index(".notebook-main .page-head h1 {"):]
    rule = rule[:rule.index("}")]
    assert "font-size: clamp(" in rule
    assert "2.5rem" in rule or "2.4rem" in rule or "2.35rem" in rule
    # Existing functional roles keep their approved tokens.
    assert "html { font-size: 28.05px; }" in css
    assert ".note { color: var(--muted); font-size: 0.85rem; }" in css
    assert ".meta { font-size: 0.88rem;" in css


def test_analytical_order_is_chart_then_search_then_cards_then_evidence_and_help(site_path):
    html = notebook_html(site_path)
    chart = html.index('<section class="notebook-chart"')
    search = html.index('<section class="notebook-search"')
    cards = html.index('<section class="notebook-selection"')
    evidence = html.index('<details class="table-details">')
    help_panel = html.index('<details class="notebook-help"')
    assert chart < search < cards < evidence < help_panel
    # Settings live after the plot, so opening them cannot move the chart top.
    assert html.index("</figure>") < html.index('id="definicoes"')
    assert html.index('<details class="notebook-chart-settings"') > html.index("</figure>")


def test_chart_controls_are_visible_and_one_authoritative_get_form(site_path):
    html = notebook_html(site_path)
    root = dom(html)
    form = chart_form(root)
    assert form.attrs.get("method", "").lower() == "get"
    assert form.attrs.get("action") == "/caderno"
    controls = form.find_all("select")
    names = [node.attrs.get("name") for node in controls]
    assert names.count("janela") == 1
    assert names.count("escala") == 1
    # The plot and its caption are outside the one settings form; the single form follows it.
    figure = one(root, "figure", "chart-figure")
    assert not has_form_ancestor(figure)
    assert form.find_all("figure") == []
    assert html.index("</figure>") < html.index('id="notebook-chart-form"')
    # Window/scale are one settings action away, after the plot, as one native GET form.
    assert html.index('name="janela"') > html.index("</figure>")
    assert html.index('name="escala"') > html.index("</figure>")
    assert len([node for node in root.find_all("form")
                if any(sel.attrs.get("name") == "janela" for sel in node.find_all("select"))]) == 1
    # The interactive range never sits in a form, so Enter on it cannot navigate.
    chart_range = one(root, "input", "chart-range")
    assert chart_range.attrs.get("type") == "range"
    assert chart_range.attrs.get("form") is None
    assert not has_form_ancestor(chart_range)
    assert 'onclick=' not in html
    # The chart form states the explicit mode; all mode still submits on, so clearing every
    # box is the reader's explicit empty, never an implicit return to all.
    assert 'name="grafico" value="on"' in html
    assert 'name="grafico" value="on"' in form_text(html)
    submit = [node for node in form.find_all("button") if node.attrs.get("type") == "submit"]
    assert submit, "the chart form needs a native submit"
    assert all(node.attrs.get("formaction") == "/caderno#grafico" for node in submit)


def form_text(html):
    match = re.search(r'<form id="notebook-chart-form".*?</form>', html, re.S)
    assert match is not None
    return match.group(0)


def test_common_period_and_each_side_source_unit_and_fetch_are_beside_the_plot(tmp_path):
    html = notebook_html(build_real_case(tmp_path))
    root = dom(html)
    figure = one(root, "figure", "chart-figure")
    caption = one(figure, "figcaption", "notebook-chart-caption")
    caption_text = visible(caption.all_text()).strip()
    # The caption carries only the last common period and sits above the drawing.
    assert caption_text == "Último período comum setembro de 2026"
    assert "Taxa de variação homóloga do IHPC - Portugal" not in caption_text
    assert html.index('class="notebook-chart-caption"') < html.index('class="chart-scroll"')

    # The legend carries names and exact common values; the adjacent source list carries
    # source/unit/fetched notes, both before the long range/readout control block.
    sources = one(figure, "ul", "notebook-chart-sources")
    text = visible(sources.all_text())
    assert "Taxa de variação homóloga do IHPC - Portugal" in text
    assert "Taxa de desemprego - Portugal" in text
    assert text.count("INE - Instituto Nacional de Estatística") == 2
    assert text.count("%") >= 2
    # Per-side fetch of the plotted period, not the series' own latest fetch.
    assert "01/11/2026" in text and "03/11/2026" in text
    assert html.index('class="chart-scroll"') < html.index('class="notebook-chart-sources"')
    assert html.index('class="notebook-chart-sources"') < html.index('class="legend"')
    assert html.index('class="notebook-chart-sources"') < html.index('class="chart-controls"')


def test_cards_distinguish_their_own_latest_period_from_the_plotted_common_period(tmp_path):
    html = notebook_html(build_real_case(tmp_path))
    root = dom(html)
    cards = one(root, "div", "cards")
    articles = cards.find_all("article", "card")
    assert len(articles) == 2
    by_label = {}
    for article in articles:
        label = one(article, "p", "card-label").all_text().strip()
        by_label[label] = article

    ihpc = by_label["Taxa de variação homóloga do IHPC - Portugal"]
    unemp = by_label["Taxa de desemprego - Portugal"]
    assert one(ihpc, "p", "card-period").all_text().strip() == "outubro de 2026"
    assert one(unemp, "p", "card-period").all_text().strip() == "setembro de 2026"

    ihpc_chart = one(ihpc, "p", "card-chart")
    unemp_chart = one(unemp, "p", "card-chart")
    assert ihpc_chart.attrs.get("data-chart-state") == "drawn"
    assert unemp_chart.attrs.get("data-chart-state") == "drawn"
    assert "setembro de 2026" in ihpc_chart.all_text()
    assert "No gráfico" in ihpc_chart.all_text()


def test_excluded_card_is_not_described_as_plotted(tmp_path):
    html = notebook_html(build_real_case(tmp_path), f"?s={HICP}&s={UNEMP}&grafico=on&g={HICP}")
    root = dom(html)
    cards = one(root, "div", "cards").find_all("article", "card")
    states = [one(card, "p", "card-chart") for card in cards]
    assert [node.attrs["data-chart-state"] for node in states] == ["drawn", "excluded"]
    assert "No gráfico" in states[0].all_text()
    assert "Fora do gráfico" in states[1].all_text()
    assert "outubro de 2026" in states[1].all_text()


def test_off_empty_and_unavailable_states_are_honest_on_the_cards(site_path):
    with client(site_path) as site:
        off = site.get(f"/caderno?s={HICP}&s={UNEMP}&grafico=off").text
        empty = site.get(f"/caderno?s={HICP}&s={UNEMP}&grafico=on").text
        unavailable = site.get(
            f"/caderno?s={HICP}&s={INACTIVE}&grafico=on&g={INACTIVE}").text

    off_root = dom(off)
    assert one(off_root, "section", "notebook-chart").attrs["data-chart-state"] == "off"
    assert {node.attrs["data-chart-state"] for node in off_root.find_all("p", "card-chart")} == {"off"}
    assert "Gráfico desativado" in one(off_root, "section", "notebook-chart").all_text()

    empty_root = dom(empty)
    assert one(empty_root, "section", "notebook-chart").attrs["data-chart-state"] == "empty"
    assert {node.attrs["data-chart-state"] for node in empty_root.find_all("p", "card-chart")} == {"empty"}
    statuses = [node.all_text() for node in empty_root.find_all("p", "card-chart")]
    assert all("No gráfico" not in text for text in statuses)

    unavailable_root = dom(unavailable)
    section = one(unavailable_root, "section", "notebook-chart")
    assert section.attrs["data-chart-state"] == "unavailable"
    card_status = one(unavailable_root, "p", "card-chart")
    assert card_status.attrs["data-chart-state"] == "unavailable"
    assert "Gráfico indisponível" in card_status.all_text()
    assert "No gráfico" not in card_status.all_text()


def test_more_than_six_implicit_series_are_not_silently_plotted(tmp_path):
    path = tmp_path / "workspace-many.db"
    db = open_db(path)
    try:
        ids = [f"ine.workspace_{index}.PT" for index in range(7)]
        specs = [make_spec(series_id, key=f"{FAMILIES[index]}.PT.M")
                 for index, series_id in enumerate(ids)]
        sync_registry(db, specs)
        for series_id in ids:
            fetch(db, series_id, {"2026-09": "1.0", "2026-10": "2.0"}, T1)
    finally:
        db.close()
    query = "?" + "&".join(f"s={series_id}" for series_id in ids)
    html = notebook_html(path, query)
    root = dom(html)
    assert one(root, "section", "notebook-chart").attrs["data-chart-state"] == "choose"
    assert {node.attrs["data-chart-state"] for node in root.find_all("p", "card-chart")} == {"choose"}
    assert "chart-data" not in html
    assert 'name="g"' in form_text(html)
    assert " checked" not in form_text(html)


def test_search_removal_and_add_links_return_to_their_work_area(site_path):
    html = notebook_html(site_path, f"?s={HICP}&q=desemprego")
    add = re.search(r'href="([^"]+)">Acrescentar ao caderno</a>', html)
    assert add is not None
    assert add.group(1).startswith(f"/caderno?s={HICP}&amp;s={UNEMP}&amp;q=desemprego")
    assert add.group(1).endswith("#grafico")

    selected = notebook_html(site_path, f"?s={HICP}&s={UNEMP}&q=desemprego")
    remove = re.search(r'href="([^"]+)">Remover do caderno</a> <span class="badge badge-quiet">'
                       r'Já no caderno</span>', selected)
    assert remove is not None and remove.group(1).endswith("#pesquisa")
    card_remove = re.search(r'class="card-remove" href="([^"]+)"', selected)
    assert card_remove is not None and card_remove.group(1).endswith("#selecao")
    canonical = re.search(r'id="ligacao-limpa" href="([^"]+)"', selected).group(1)
    assert "#" not in canonical
    # Fragments only: no new statistical parameter appears in any link.
    notebook_urls = " ".join(re.findall(r'href="(/caderno[^"]*)"', html + selected))
    names = set(re.findall(r"[?&]([a-z]+)=", notebook_urls))
    assert names <= {"s", "q", "g", "grafico", "escala", "janela", "dia"}


def test_search_form_preserves_every_addressed_reference_and_chart_setting(site_path):
    query = (f"?s={HICP}&s={UNEMP}&s={INACTIVE}&grafico=on&g={HICP}"
             "&escala=dupla&janela=5a&dia=2026-11-01&q=desemprego")
    html = notebook_html(site_path, query)
    search_form = re.search(r'<form id="notebook-search-form".*?</form>', html, re.S)
    assert search_form is not None
    body = search_form.group(0)
    for series_id in (HICP, UNEMP, INACTIVE):
        assert f'name="s" value="{series_id}"' in body
    assert 'name="grafico" value="on"' in body
    assert f'name="g" value="{HICP}"' in body
    assert 'name="escala" value="dupla"' in body
    assert 'name="janela" value="5a"' in body
    assert 'name="dia" value="2026-11-01"' in body


def test_mount_prefix_is_preserved_on_every_new_action(site_path):
    query = f"?s={HICP}&s={UNEMP}&grafico=on&g={HICP}"
    with client(site_path) as site:
        response = site.get(f"/caderno{query}", headers={"X-Forwarded-Prefix": "/dados"})
    assert response.status_code == 200
    html = response.text
    assert 'action="/dados/caderno"' in form_text(html)
    assert 'formaction="/dados/caderno#grafico"' in form_text(html)
    assert 'href="/dados/caderno?s=' in html
    assert 'class="button-quiet" href="#pesquisa"' in html
    assert 'class="button-quiet" href="#definicoes"' in html
    assert 'href="/caderno' not in html and 'action="/caderno' not in html


def test_help_disclosure_keeps_the_moved_explanations_below_the_workspace(site_path):
    html = notebook_html(site_path)
    root = dom(html)
    help_panel = one(root, "details", "notebook-help")
    text = visible(help_panel.all_text())
    assert "Qualquer pessoa com esta ligação pode abrir a seleção." in text
    assert "A seleção não é um retrato histórico." in text
    assert "Cada abertura mostra os valores atuais." in text
    assert "Comparar curvas no mesmo gráfico não estabelece uma relação de causa." in text


def test_print_rules_keep_the_caption_and_restore_the_svg(site_path):
    css = CSS.read_text(encoding="utf-8")
    print_block = css[css.index("@media print {"):]
    assert ".notebook-chart-caption" not in print_block
    assert ".notebook-chart-sources" not in print_block
    assert ".notebook-caveat { display: block; }" in print_block
    assert ".chart-scroll { overflow: visible; }" in print_block
    assert ".chart-wrap { min-width: 0; }" in print_block
    assert ".chart-canvas, .chart-controls, .chart-hint { display: none !important; }" in print_block
    html = notebook_html(site_path)
    assert 'class="notebook-chart-caption"' in html
    assert 'class="notebook-chart-sources"' in html
    assert 'src="/static/js/prumo-charts' in html


def test_off_survives_a_window_or_scale_submission(site_path):
    html = notebook_html(site_path, f"?s={HICP}&s={UNEMP}&grafico=off")
    form = chart_form(dom(html))
    assert 'name="grafico" value="off"' in form_text(html)
    fields = form_fields(form)
    assert ("grafico", "off") in fields

    submitted = submit_fields(site_path, fields, replace={"janela": "5a", "escala": "dupla"})
    root = dom(submitted)
    assert one(root, "section", "notebook-chart").attrs["data-chart-state"] == "off"
    assert 'name="grafico" value="off"' in form_text(submitted)
    assert "Ativar gráfico" in submitted
    assert "chart-data" not in submitted


def test_explicit_empty_survives_a_settings_submission(site_path):
    html = notebook_html(site_path, f"?s={HICP}&s={UNEMP}&grafico=on")
    form = chart_form(dom(html))
    assert 'name="grafico" value="on"' in form_text(html)
    fields = form_fields(form)
    assert not any(name == "g" for name, _ in fields)

    submitted = submit_fields(site_path, fields, replace={"janela": "5a", "escala": "dupla"})
    root = dom(submitted)
    assert one(root, "section", "notebook-chart").attrs["data-chart-state"] == "empty"
    assert "Não há séries escolhidas para o gráfico" in submitted


def test_all_mode_clearing_every_box_submits_an_explicit_empty(site_path):
    html = notebook_html(site_path)
    form = chart_form(dom(html))
    assert 'name="grafico" value="on"' in form_text(html)
    fields = form_fields(form)
    assert sum(name == "g" for name, _ in fields) == 2

    submitted = submit_fields(site_path, fields, drop={"g"})
    root = dom(submitted)
    assert one(root, "section", "notebook-chart").attrs["data-chart-state"] == "empty"
    assert "Não há séries escolhidas para o gráfico" in submitted


def test_blank_chart_states_do_not_render_empty_evidence_disclosures(site_path):
    blank_queries = (
        f"?s={HICP}&s={UNEMP}&grafico=off",
        f"?s={HICP}&s={UNEMP}&grafico=on",
        f"?s={HICP}&s={INACTIVE}&grafico=on&g={INACTIVE}",
    )
    for query in blank_queries:
        root = dom(notebook_html(site_path, query))
        assert not root.find_all("details", "notebook-definitions"), query
        assert not root.find_all("details", "table-details"), query
        assert not root.find_all("details", "provenance-details"), query

    ready = dom(notebook_html(site_path))
    assert one(ready, "details", "notebook-definitions")
    assert one(ready, "details", "table-details")
    assert one(ready, "details", "provenance-details")


def test_redundant_breadcrumb_and_mobile_plot_floor_overrides_are_gone(site_path):
    html = notebook_html(site_path)
    root = dom(html)
    assert not root.find_all("nav", "crumbs")
    assert ".notebook-chart .chart-enhanced .chart-wrap { min-height: 0; }" not in CSS.read_text(
        encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert ".notebook-chart .chart-enhanced .chart-wrap" not in css
    assert "min-width: 660px; min-height: 264px;" in css
    assert ".chart-enhanced .chart-wrap { min-width: 0; }" in css
    # The caption's mobile position is its real DOM position, not a CSS order swap.
    assert ".notebook-chart .chart-figure .chart-shell { order:" not in css
    assert ".notebook-chart .chart-figure .notebook-chart-caption { order:" not in css


def test_snapshot_and_causality_caveats_are_visible_outside_the_print_hidden_help(site_path):
    html = notebook_html(site_path)
    root = dom(html)
    help_panel = one(root, "details", "notebook-help")
    caveat = one(root, "p", "notebook-caveat")
    caveat_text = visible(caveat.all_text())
    assert "A seleção não é um retrato histórico." in caveat_text
    assert "Comparar curvas no mesmo gráfico não estabelece uma relação de causa." in caveat_text
    assert not has_ancestor(caveat, help_panel)
    assert 'class="note notebook-caveat"' in html


def test_settings_fragment_targets_content_inside_the_native_disclosure(site_path):
    root = dom(notebook_html(site_path))
    settings = one(root, "details", "notebook-chart-settings")
    target = one(settings, "div", "notebook-chart-options")
    assert target.attrs["id"] == "definicoes"
    assert "id" not in settings.attrs
    assert has_ancestor(target, settings)
    css = CSS.read_text(encoding="utf-8")
    assert "repeat(auto-fit, minmax(min(14rem, 100%), 1fr))" in css
