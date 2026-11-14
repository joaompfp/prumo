"""Independent verifier for INE (Statistics Portugal), spec 6b:

    collector:  JSON Database API (/ine/json_indicador/pindica.jsp?op=2 → application/json)
    verifier:   bddXplorer server-rendered statistical table
                (/bddXplorer/htdocs/bddXplorer04.jsp → text/html)

A different endpoint and a different format, owned by INE's publication UI. The table is INE's
*published rendering*: ',' decimal, space thousands separators, the conventional sign appended
to the figure ('5,6 &'), and the unit symbol shown in the table header. The collector's JSON
`valor` token drops trailing zeros ('2' where the table shows '2,0') — verification compares
NUMERICALLY (ingest.verify compares exact Decimals), which is Ruling AB.

Mechanics (reverse-engineered and cross-checked live 2026-11-11; see the Task 10 report):

1.  The channel requires header `Referer: https://www.ine.pt/`; without it the server answers
    302 to https://www.ine.pt with an empty body (that 302 is what "needs a browser" meant).
2.  The indicator page (GET ...?indOcorrCod=<varcd>&contexto=bd&lang=PT) carries an HTML form
    whose hidden input `xmlDocHidden` is a `Classificacoes` XML document: the indicator's
    dimensions and, per dimension, its category tree with `selected` flags. Period categories
    have Id 'periodo_…', a Portuguese label ('Setembro de 2026', '2024') and an `order`
    attribute with the period's end date ('2026-09-30').
3.  Setting `selected` to 'true' only on the wanted period category and on the category pinning
    every other dimension, then sending the whole form back as the GET query, renders the table
    of exactly that cut. The collector's dimension numbering maps onto the page's classes as:
    Dim1 = the type='time' class (period), Dim2 = the type='geo' class, Dim3.. = the type='dim'
    classes in ascending `order` attribute. The shipped tree may lack deep categories (e.g. the
    CAE *divisions* of indicator 0011889 — only the sections B-E ship); a missing `cod_categ` is
    then selected by inserting one Categoria node for it as a direct child of that class's root
    category. That recipe was validated live against 0011889 divisions 08/10/35/38 (the rendered
    rows carry the requested code and the values match the JSON channel exactly); injecting
    under a wrong deeper parent renders 'x' dummy rows instead, so the cut assertions below
    (exactly one matching cell, echoed selection equals the request, no other period visible)
    are what make this fail-closed.
4.  The table (class 'dados', summary 'Quadro estatístico/Statistical table') is parsed as a
    grid honouring rowspan/colspan: header rows give per-column dimension codes, the period
    label when the period is laid out in columns, and one unit-symbol cell per column; data rows
    give the period label when in rows, the row-dimension codes and the cell text. Everything is
    asserted: exactly one row and one column may match the pinned cut; every period visible in
    the table must normalize to the item's period; the response's echoed selection must equal
    the requested cut; the table's unit symbol and the document's own `simbolo` attribute must
    agree, and `potencia` must be '0'; an unknown sign or unit symbol raises instead of
    guessing. An INE error page ('Ocorreu um erro…') has no dados table and raises.

Parsing note: the page is a 20-180 KB JSP template of fixed shape. The statistical table is
extracted as a substring, its footnote anchors and 'Nota(s)' rows removed, and parsed with
xml.etree (after those removals the observed bodies are well-formed: only XML-native `&amp;`
escapes occur, everything else is raw UTF-8). The form's hidden inputs are single-line
`<input type="hidden" ...>` elements. html.parser is NOT used: a subclass would need
`super().__init__`, which the verifier independence allowlist (Ruling S) forbids.

INDEPENDENCE: this module shares NO code with the collector (a shared helper module is forbidden
by register_verifier and checked at runtime by assert_verifier_independent). The small
native_code parsing, the conventional-sign table and the unit-symbol table are DUPLICATED ON
PURPOSE: if the two copies ever disagree, verification fails loudly.

Requests are paced by the injected Http client (RequestsHttp throttles every request to ≤1/s by
default) — the verifier adds no sleeping of its own so tests on recorded fixtures stay fast.

Registration: the Task 17 CLI calls register_verifier(INEVerifier()).
"""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from ingest.http import Http
from ingest.models import normalize_period
from ingest.verifiers import BlindItem, ItemResult, VerifierUnavailable

PAGE_URL = "https://www.ine.pt/bddXplorer/htdocs/bddXplorer04.jsp"
REFERER = "https://www.ine.pt/"  # mandatory: without it INE answers 302 + empty body
MIN_PAGE_BYTES = 5000  # a real indicator page is ~18-500 KB; an INE error page is ~2 KB

# DUPLICATE of the INE conventional-sign mapping in ingest/flags.py, ON PURPOSE (see docstring).
# Keys are the symbols of the official legend (sinais.jsp); the published figure carries them
# appended after a space ('5,6 &').
_SIGN_FLAG = {"&": "provisional", "//": "provisional", "*": "revised",
              "\u2534": "break", "\u201c": "estimated",  # ┴ series break, “ estimate
              "\u00a7": "normal"}  # § quality caveat: no flag change, BY DECISION (M2)
_SIGN_NO_VALUE = frozenset({"\u2026", "x", "-"})  # … confidential, x not available, - null/NA
_STRONGEST_FIRST = ("break", "provisional", "estimated", "revised", "normal")

# DUPLICATE of the registry unit-label ↔ INE unit pairing (tests/ingest/test_registry_ine_units.py),
# ON PURPOSE, but keyed by the SYMBOL bddXplorer shows in the table's unit header cell ('%',
# '€', 'N.º'); '-' means a bare index whose base year is in the table title.
_UNIT_OF_SYMBOL = {"%": "%", "€": "EUR", "N.º": "N.º"}
_INDEX_SYMBOL = "-"
_BASE_YEAR_RE = re.compile(r"Base\s*-?\s*((?:19|20)\d{2})")

_NUMBER_LIKE = re.compile(r"[0-9\s\xa0\u202f,.+-]+")

_HIDDEN_RE = re.compile(r"<input type=\"hidden\" name=\"([^\"]+)\" id=\"[^\"]*\" value=\"([^\"]*)\"/?>")
_DADOS_RE = re.compile(r"<table class='dados'[^>]*summary='Quadro estat")
_TNOTES_RE = re.compile(r"(?s)<tr><td class='TNotes'.*?</tr>")
_ANCHOR_RE = re.compile(r"(?s)<a [^>]*href='#\d+'[^>]*>.*?</a>")


def _native(code: str | None) -> tuple[str, list[tuple[str, str]]]:
    """'<7-digit varcd>:Dim2=<code>,Dim3=<code>,...' -> (varcd, [("Dim2", code), ...]).

    DUPLICATE of the collector's parse_native_code, ON PURPOSE (see module docstring)."""
    varcd, sep, rest = (code or "").partition(":")
    if not (sep and len(varcd) == 7 and varcd.isdigit() and rest):
        raise ValueError(f"INE native_code must be '<7-digit varcd>:Dim2=<code>,...', got {code!r}")
    pairs = []
    for n, part in enumerate(rest.split(","), start=2):
        dim, eq, val = part.partition("=")
        if dim != f"Dim{n}" or not eq or not val or any(c in val for c in "=:, "):
            raise ValueError(f"malformed INE native_code {code!r} at {part!r}")
        pairs.append((dim, val))
    return varcd, pairs


def _xml(text: str) -> ET.Element:
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        # a bare '&' in a label would break XML: escape strays and retry once
        try:
            return ET.fromstring(re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;)", "&amp;", text))
        except ET.ParseError as e:
            raise ValueError(f"XML does not parse: {e}") from e


def _hidden_fields(text: str) -> dict[str, str]:
    """The hidden <input> fields of the page's form (one line each in the JSP template)."""
    fields = dict(_HIDDEN_RE.findall(text))
    if "xmlDocHidden" not in fields:
        raise ValueError(f"page without the xmlDocHidden form XML (error page or a layout "
                         f"change): {text[:200]!r}")
    return fields


@dataclass
class _Cell:
    tag: str  # 'th' | 'td'
    cls: str
    rowspan: int
    colspan: int
    text: str = ""
    code: str | None = None  # content of a <span class='dimensionCode'>CODE:</span>


def _dados_table(text: str) -> ET.Element:
    """The statistical table as an XML element: substring extraction + removal of the footnote
    anchors and note rows (which carry prose with HTML constructs that are not well-formed
    XML). In every recorded page the remainder contains no nested tables and no entities beyond
    XML's own."""
    start = _DADOS_RE.search(text)
    if start is None:
        raise ValueError(f"no dados table in the page (INE error page?): {text[:200]!r}")
    end = text.find("</table>", start.end())
    if end < 0 or "<table" in text[start.end():end]:
        raise ValueError("the dados table is truncated or nests another table (unexpected)")
    body = _TNOTES_RE.sub("", text[start.start():end + len("</table>")])
    body = _ANCHOR_RE.sub("", body)  # footnote anchors '(<a href='#1' .../>1</a>)'
    try:
        return ET.fromstring(body)
    except ET.ParseError as e:
        raise ValueError(f"the dados table is not well-formed after cleaning: {e}") from e


def _rows_of(tbl: ET.Element) -> list[tuple[str, list[_Cell]]]:
    """(tr class, cells) for every row of the dados table; text with whitespace collapsed."""
    rows = []
    for tr in tbl.iter("tr"):
        cells = []
        for el in tr:
            if el.tag not in ("th", "td"):
                continue
            rowspan, colspan = el.get("rowspan", "1"), el.get("colspan", "1")
            if not (rowspan.isdigit() and colspan.isdigit()):
                raise ValueError("non-numeric rowspan/colspan in the dados table")
            code = None
            for span in el.iter("span"):
                if "dimensionCode" in span.get("class", "").split():
                    code = "".join(span.itertext()).strip().removesuffix(":").strip()
            text = " ".join("".join(el.itertext()).split())
            cells.append(_Cell(el.tag, el.get("class", ""), int(rowspan), int(colspan),
                               text, code))
        rows.append((tr.get("class", ""), cells))
    return rows


@dataclass
class _ClassDim:
    """One dimension ('class') of the indicator's Classificacoes XML."""
    el_id: str  # CLASS tag suffix ('periodo', '4095002', ...)
    label: str
    tipo: str  # 'time' | 'geo' | 'dim'
    disposicao: str  # 'linha' | 'coluna'
    order: int
    maxlevel: int


def _categories(root: ET.Element, cd: _ClassDim) -> list[ET.Element]:
    """Every <Categoria> of a class, recursively."""
    el = root.find(f".//CLASS_{cd.el_id}")
    if el is None:
        raise ValueError(f"class CLASS_{cd.el_id} ({cd.label!r}) missing from the XML")
    return list(el.iter("Categoria"))


@dataclass
class _Page:
    varcd: str
    simbolo: str
    potencia: str
    label: str
    form: dict[str, str]
    xml_text: str
    period: _ClassDim
    geo: _ClassDim
    dims: list  # type='dim' classes, ascending `order` (Dim3, Dim4, ...)

    def dim_map(self) -> list[tuple[str, _ClassDim]]:
        """Dim2 -> the geo class; Dim3.. -> the type='dim' classes in ascending `order`."""
        return [("Dim2", self.geo)] + [(f"Dim{n + 3}", cd) for n, cd in enumerate(self.dims)]


def _page_from(body: bytes, varcd: str) -> _Page:
    text = body.decode("utf-8")
    form = _hidden_fields(text)
    xml_text = form["xmlDocHidden"]
    root = _xml(xml_text)
    if root.tag != "Classificacoes" or root.get("indicadorOcorrCod") != varcd:
        raise ValueError(f"page Classificacoes for {root.get('indicadorOcorrCod')!r}, "
                         f"expected {varcd!r}")
    period = geo = None
    dims = []
    for el in root:
        if not el.tag.startswith("CLASS_"):
            continue
        tipo, disp = el.get("type", ""), el.get("disposicao", "")
        order, maxlevel = el.get("order", ""), el.get("maxlevel", "1")
        if tipo not in ("time", "geo", "dim") or disp not in ("linha", "coluna"):
            raise ValueError(f"unexpected class attributes type={tipo!r} disposicao={disp!r}")
        if not order.isdigit() or not maxlevel.isdigit():
            raise ValueError(f"bad order/maxlevel on class {el.get('Id')!r}")
        if el.find("Categorias") is None:
            raise ValueError(f"class {el.get('Id')!r} without Categorias")
        cat = _ClassDim(el.get("Id", ""), el.get("label", ""), tipo, disp,
                        int(order), int(maxlevel))
        if tipo == "time":
            if period is not None:
                raise ValueError(f"page {varcd} with more than one time dimension")
            period = cat
        elif tipo == "geo":
            if geo is not None:
                raise ValueError(f"page {varcd} with more than one geo dimension")
            geo = cat
        else:
            dims.append(cat)
    if period is None or geo is None:
        raise ValueError(f"page {varcd} lacks its time or geo dimension")
    return _Page(varcd, root.get("simbolo", ""), root.get("potencia", ""),
                 root.get("label", ""), form, xml_text, period, geo,
                 sorted(dims, key=lambda cd: cd.order))


def _pinned(page: _Page, pins: list[tuple[str, str]]) -> dict[str, str]:
    """native_code pins -> {class el_id: cod_categ}; the cut must pin every non-time class."""
    mapping = page.dim_map()
    if sorted(d for d, _ in pins) != sorted(d for d, _ in mapping):
        raise ValueError(f"native_code pins {sorted(d for d, _ in pins)} but page {page.varcd} "
                         f"has dimensions {sorted(d for d, _ in mapping)}")
    codes = dict(pins)
    return {cd.el_id: codes[d] for d, cd in mapping}


def _select(page: _Page, period: str, frequency: str, pins: list[tuple[str, str]]) -> dict:
    """The form fields with xmlDocHidden rewritten to select exactly the wanted cut: one period
    category and one category per other dimension. A pinned category missing from the shipped
    tree (deep tree levels, e.g. CAE divisions) is injected as a direct child of that class's
    root category — validated live on 0011889 against the JSON channel; the response table
    carries the category's own code, so the evidence identifies what was read."""
    if frequency not in ("A", "M"):
        raise ValueError(f"this channel was probed for frequencies A and M; got {frequency!r}")
    by_class = _pinned(page, pins)
    root = _xml(page.xml_text)  # fresh parse per item: the tree is mutated below

    selected = 0
    for cat in _categories(root, page.period):
        try:
            canonical = normalize_period(cat.get("label", ""), frequency)
        except ValueError as e:
            raise ValueError(f"period label {cat.get('label')!r} does not normalize: {e}") from e
        wanted = canonical == period
        if wanted:
            end = cat.get("order", "")[:4] if frequency == "A" else cat.get("order", "")[:7]
            if end != period:  # the label and the period's end date must tell the same period
                raise ValueError(f"period label {cat.get('label')!r} but end date "
                                 f"{cat.get('order')!r}")
            selected += 1
        cat.set("selected", "true" if wanted else "false")
    if selected != 1:
        raise ValueError(f"period {period!r} is offered {selected}x by page {page.varcd} "
                         f"(must be offered exactly once)")

    for cd in [page.geo, *page.dims]:
        code = by_class[cd.el_id]
        cats = _categories(root, cd)
        matches = [c for c in cats if c.get("cod_categ") == code]
        if len(matches) > 1:
            raise ValueError(f"cod_categ {code!r} appears {len(matches)}x in class "
                             f"{cd.label!r} of page {page.varcd}")
        for cat in cats:
            cat.set("selected", "false")
        if matches:
            matches[0].set("selected", "true")
            continue
        # deep category absent from the shipped tree: inject it as a direct child of the
        # class's root category (see docstring)
        categorias = root.find(f".//CLASS_{cd.el_id}/Categorias")
        if categorias is None or not list(categorias):
            raise ValueError(f"pinned category {code!r} absent from class {cd.label!r} and the "
                             f"class has no root category to inject it under (page {page.varcd})")
        rootnode = list(categorias)[0]
        node = ET.SubElement(rootnode, "Categoria")
        node.set("Id", f"{cd.el_id}_{code}_root")
        node.set("cod_categ", code)
        node.set("nivel", str(int(rootnode.get("nivel", "1")) + 1))
        node.set("order", "999")
        node.set("selected", "true")
        node.set("opened", "false")
        node.set("label", code)
    form = dict(page.form)
    form["xmlDocHidden"] = ET.tostring(root, encoding="unicode")
    return form


def _placement(rows: list[tuple[str, list[_Cell]]]):
    """(row, col) grid honouring rowspan/colspan: per-row cells' start columns (aligned with
    each row's cell list)."""
    occ: dict[tuple[int, int], _Cell] = {}
    starts: dict[int, list[int]] = {}
    for r, (_, cells) in enumerate(rows):
        c = 0
        for cell in cells:
            while (r, c) in occ:
                c += 1
            for dr in range(cell.rowspan):
                for dc in range(cell.colspan):
                    occ[(r + dr, c + dc)] = cell
            starts.setdefault(r, []).append(c)
    return occ, starts


def _unit(symbol: str, simbolo: str, label: str) -> str:
    """observed_unit: the unit symbol shown in the table's unit header cell, mapped fail-closed
    onto the canonical registry unit; the document's own simbolo attribute must agree. A bare
    index ('-') takes its base year from the table title ('Base - 2021')."""
    sym = symbol.strip()
    if sym != simbolo.strip():
        raise ValueError(f"table unit symbol {sym!r} != document simbolo {simbolo!r}")
    if sym in _UNIT_OF_SYMBOL:
        return _UNIT_OF_SYMBOL[sym]
    if sym == _INDEX_SYMBOL:
        base = _BASE_YEAR_RE.search(label)
        if base is None:
            raise ValueError(f"index unit '-' but no base year in the table title {label!r}")
        return f"index_{base.group(1)}=100"
    raise ValueError(f"unknown INE unit symbol {sym!r} in the table")


def _value(text: str) -> tuple[str | None, str | None]:
    """'5,6 &' -> ('5,6', 'provisional'); 'x' / '…' / '-' -> (None, None). A trailing token that
    is neither part of the number nor a reviewed sign raises (never silently 'normal')."""
    text = text.replace("−", "-").strip()  # typographic minus -> ASCII
    if not text:
        raise ValueError("empty value cell")
    if text in _SIGN_NO_VALUE:
        return None, None  # a no-value cell (e.g. confidential): not found, would be a mismatch
    parts = text.split()
    flags = []
    while parts and parts[-1] in _SIGN_FLAG:
        flags.append(_SIGN_FLAG[parts.pop()])
    if not parts or not _NUMBER_LIKE.fullmatch(" ".join(parts)) \
            or not any(c.isdigit() for c in parts[-1]):
        raise ValueError(f"unreadable INE table cell {text!r}")
    if not flags:
        return " ".join(parts), "normal"
    return " ".join(parts), next(f for f in _STRONGEST_FIRST if f in set(flags))


def _cut(body: bytes, page: _Page, period: str, frequency: str,
         pins: list[tuple[str, str]]) -> tuple[str, str, str, str]:
    """The matched cell's text, its column's unit symbol and the response's own simbolo/label;
    raises unless the table shows exactly the requested cut."""
    text = body.decode("utf-8")
    form = _hidden_fields(text)
    root = _xml(form["xmlDocHidden"])
    if root.get("indicadorOcorrCod") != page.varcd:
        raise ValueError(f"table for {root.get('indicadorOcorrCod')!r}, asked {page.varcd!r}")
    if root.get("potencia", "") != "0":
        raise ValueError(f"potencia {root.get('potencia')!r} != 0: table values would be scaled")
    # the response echoes the selection; it must be exactly the requested cut
    sel_periods = [c.get("label", "") for c in root.findall(".//CLASS_periodo//Categoria")
                   if c.get("selected") == "true"]
    if len(sel_periods) != 1 or normalize_period(sel_periods[0], frequency) != period:
        raise ValueError(f"response period selection {sel_periods!r} != {period!r}")
    # the echo repeats an injected deep category once per candidate parent it was tried under;
    # compare per class as a SET (each class is pinned to exactly one cod_categ by contract)
    for cd in [page.geo, *page.dims]:
        el = root.find(f".//CLASS_{cd.el_id}")
        sel = {c.get("cod_categ") for c in el.iter("Categoria")
               if c.get("selected") == "true"}
        expected_code = _pinned(page, pins)[cd.el_id]
        if sel != {expected_code}:
            raise ValueError(f"response selection in class {cd.label!r} is {sorted(sel)}, "
                             f"pinned {expected_code!r}")

    rows = _rows_of(_dados_table(text))
    if not rows:
        raise ValueError(f"selection response has an empty dados table: {text[:200]!r}")
    header_idx = [i for i, (cls, cells) in enumerate(rows)
                  if not cls.startswith("TRow") and any(c.tag == "th" for c in cells)]
    data_idx = [i for i, (cls, _) in enumerate(rows) if cls.startswith("TRow")]
    if not header_idx or not data_idx or header_idx[-1] >= data_idx[0]:
        raise ValueError("dados table without the expected header/data split")
    occ, starts = _placement(rows)
    unit_row = header_idx[-1]

    expected = _pinned(page, pins)
    row_wanted = tuple(expected[cd.el_id] for cd in [page.geo, *page.dims]
                       if cd.disposicao == "linha")
    col_wanted = tuple(expected[cd.el_id] for cd in [page.geo, *page.dims]
                       if cd.disposicao == "coluna")

    # per-column identity: codes (every header code cell), period label and unit symbol
    col_codes: dict[int, tuple] = {}
    col_period: dict[int, str] = {}
    col_unit: dict[int, str] = {}
    for r in range(unit_row + 1):
        for cell, start in zip(rows[r][1], starts[r]):
            if cell.tag != "th":
                continue
            if r == unit_row:
                for dc in range(cell.colspan):
                    col_unit[start + dc] = cell.text
            elif cell.code:
                for dc in range(cell.colspan):
                    col_codes[start + dc] = (*col_codes.get(start + dc, ()), cell.code)
            elif "THeader" in cell.cls:
                try:
                    label = normalize_period(cell.text, frequency)
                except ValueError:
                    continue  # dimension titles and the indicator title are not period labels
                for dc in range(cell.colspan):
                    col_period[start + dc] = label

    matched: list[tuple[str, str]] = []  # (cell text, unit symbol)
    row_periods: set[str] = set()
    current_period: str | None = None
    for r in data_idx:
        _, cells = rows[r]
        row_codes: list[str] = []
        for cell, start in zip(cells, starts[r]):
            if cell.cls == "normal":
                if cell.code:
                    row_codes.append(cell.code)
                else:
                    current_period = normalize_period(cell.text, frequency)
                    row_periods.add(current_period)
            elif tuple(col_codes.get(start, ())) == col_wanted \
                    and tuple(row_codes) == row_wanted:
                label = current_period if page.period.disposicao == "linha" \
                    else col_period.get(start)
                unit = col_unit.get(start)
                if label is None or unit is None:
                    raise ValueError("matched cell lacks its period label or unit symbol")
                matched.append((cell.text, unit))
    # every period visible anywhere in the table must be the wanted one: if the server ignored
    # the cut or answered a different period, this fails loudly instead of echoing the request
    visible = row_periods if page.period.disposicao == "linha" else set(col_period.values())
    if visible != {period}:
        raise ValueError(f"table shows period(s) {sorted(visible)}, expected exactly {period!r}")
    if len(matched) != 1:
        raise ValueError(f"{len(matched)} cells match the pinned cut (must be exactly 1)")
    return matched[0][0], matched[0][1], root.get("simbolo", ""), root.get("label", "")


def _structure(page: _Page) -> tuple:
    return page.varcd, page.period, page.geo, page.dims


def _decide(item: BlindItem, body: bytes, page: _Page, url: str) -> ItemResult:
    """One item read from its selection response (shared by check and reread). The response's
    own Classificacoes echo must describe the same classes as `page`."""
    varcd, pins = _native(item.spec.native_code)
    if _structure(_page_from(body, varcd)) != _structure(page):
        raise ValueError(f"selection response for {varcd} describes other classes than its "
                         f"indicator page")
    cell_text, unit_symbol, simbolo, label = _cut(body, page, item.period, item.spec.frequency,
                                                  pins)
    observed_text, observed_flag = _value(cell_text)
    return ItemResult(series_id=item.series_id, period=item.period, observed_text=observed_text,
                      evidence_url=url, observed_decimal=",",
                      observed_unit=_unit(unit_symbol, simbolo, label),
                      observed_flag=observed_flag, evidence=body)


class INEVerifier:
    """See the module docstring. One indicator-page fetch per indicator per check() call, then
    one selection request per sampled item; every ItemResult carries the selection response's
    HTML as evidence bytes. That response echoes the indicator's whole Classificacoes document
    (asserted equal to the indicator page's classes), so `reread` re-decides an item from the
    selection HTML alone."""
    source_name = "ine"
    not_compared: dict[str, str] = {}  # value, unit symbol and conventional sign all exposed

    def request_key(self, item: BlindItem):
        return item.spec.native_code, item.period  # one selection request per item

    def reread(self, evidence: bytes, item: BlindItem) -> ItemResult:
        varcd, _pins = _native(item.spec.native_code)
        return _decide(item, evidence, _page_from(evidence, varcd), "")

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]:
        pages: dict[str, _Page] = {}
        results: list[ItemResult] = []
        for item in items:
            varcd, pins = _native(item.spec.native_code)
            if varcd not in pages:
                r = http.get(PAGE_URL, headers={"Referer": REFERER},
                             params={"indOcorrCod": varcd, "contexto": "bd", "lang": "PT"})
                if not 200 <= r.status < 300:
                    raise VerifierUnavailable(f"INE page for {varcd} answered HTTP {r.status}")
                if len(r.body) < MIN_PAGE_BYTES:
                    raise ValueError(f"INE page for {varcd} is only {len(r.body)} B — error "
                                     f"page or a missing Referer header (302+empty without it)")
                pages[varcd] = _page_from(r.body, varcd)
            page = pages[varcd]
            form = _select(page, item.period, item.spec.frequency, pins)
            r = http.get(PAGE_URL, headers={"Referer": REFERER}, params=form)
            if not 200 <= r.status < 300:
                raise VerifierUnavailable(f"INE selection for {item.series_id}/{item.period} "
                                          f"answered HTTP {r.status}")
            results.append(_decide(item, r.body, page, r.url))
        return results
