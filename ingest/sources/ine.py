"""INE (Statistics Portugal) source adapter: the JSON database API.

    GET https://www.ine.pt/ine/json_indicador/pindica.jsp
        ?op=2&varcd=<varcd>&lang=PT&Dim1=T&Dim2=<c>[,<c>...]&Dim3=<c>[,<c>...]...

Registry contract (`SeriesSpec.native_code`), shared by every INE series:

    <varcd>:Dim2=<code>,Dim3=<code>,...

  - `varcd` is INE's 7-digit indicator code; every dimension of the indicator except Dim1 (the
    reference period, always fetched whole with Dim1=T) is pinned to exactly one category code,
    in order Dim2, Dim3, ... with no gap, e.g. `0011889:Dim2=PT,Dim3=C` (industrial production
    index, Portugal, manufacturing). Dimensions and codes are those of INE's metadata API
    (`pindicaMeta.jsp?varcd=..`, `Dimensoes`).
  - so one native_code identifies exactly one INE cell series. In the payload Dim2 is the entry's
    `geocod` and DimN (N >= 3) its `dim_N`.
`SeriesSpec.url` is the indicator's public page `https://www.ine.pt/xurl/indx/<varcd>`.

Requests: one per (varcd, dimension names) group; each dimension is sent as the comma-joined
sorted set of the group's codes (INE answers the cartesian product; unrequested combinations are
ignored), Dim1=T (full history, so revisions are seen). INE caps a call at ~40k cells, far above
any group in the registry. INE is SLOW: 17-45 s per request were measured, trade indicators
longer (see the Task 10 report), so the caller's RequestsHttp needs a generous timeout.

Parsing: the value handed over is INE's machine token `valor` (a JSON string, '.' decimal,
registry `decimal: '.'`), verbatim. INE also sends `ind_string`, the formatted figure as
published ('2,40', '5 652 560 322', '5,0 &' with the conventional sign appended); it keeps
trailing zeros that `valor` drops ('2.4'). We do not hand it over (switching INE to ',' would
re-quarantine the whole legacy import), but every cell's `ind_string` must denote the same number
as `valor` (and carry the same sign) or the parse raises: the two renderings of one payload must
agree. Periods are INE's Portuguese labels ('Setembro de 2025', '2025', '3.º Trimestre de 2025'),
handed over as-is (validate() normalises them). The conventional sign (`sinal_conv` +
`sinal_conv_desc`) is mapped by `ingest.flags.map_ine_flag` ('normal' stored explicitly); a cell
whose sign stands instead of a value ('x' not available, '-' null / not applicable) is handed over
with value None (quarantined non_numeric). `unit_raw` is None: INE gives the unit once per
indicator in the metadata API, not per cell; the label pairing is checked by
tests/ingest/test_registry_ine_units.py.
Raises on anything unexpected: HTML or non-JSON body, INE's {"Sucesso": {"Falso": ..}} error
object, another varcd than requested, duplicate period keys or cells, dimensions differing from
native_code, the indicator's latest period (`UltimoPref`) missing from the payload, unknown signs.
"""
import json
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation

from ingest.flags import map_ine_flag
from ingest.http import Http
from ingest.models import SeriesSpec
from ingest.sources import RawResponse
from ingest.validate import RawRow

BASE_URL = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
PAGE_URL = "https://www.ine.pt/xurl/indx/"

Key = tuple[tuple[str, str], ...]  # (("Dim2", code), ("Dim3", code), ...)


def parse_native_code(code: str | None) -> tuple[str, Key]:
    """'<varcd>:Dim2=<c>,Dim3=<c>,...' -> (varcd, (("Dim2", c), ...)); ValueError if malformed."""
    varcd, sep, rest = (code or "").partition(":")
    if not (sep and len(varcd) == 7 and varcd.isdigit() and rest):
        raise ValueError(f"INE native_code must be '<7-digit varcd>:Dim2=<code>,...', got {code!r}")
    pairs = []
    for n, part in enumerate(rest.split(","), start=2):
        dim, eq, val = part.partition("=")
        if dim != f"Dim{n}" or not eq or not val or any(c in val for c in "=:, "):
            raise ValueError(f"malformed INE native_code {code!r} at {part!r} "
                             f"(expected Dim{n}=<code>; Dim1 is the period and never pinned)")
        pairs.append((dim, val))
    return varcd, tuple(pairs)


def _entry_field(dim: str) -> str:
    return "geocod" if dim == "Dim2" else "dim_" + dim[3:]


def _groups(specs: list[SeriesSpec]) -> list[tuple[str, tuple[str, ...], list[SeriesSpec]]]:
    """(varcd, dimension names, specs) per request, in a deterministic order."""
    by: dict[tuple[str, tuple[str, ...]], list[SeriesSpec]] = {}
    for s in specs:
        varcd, key = parse_native_code(s.native_code)
        by.setdefault((varcd, tuple(d for d, _ in key)), []).append(s)
    return [(varcd, dims, members) for (varcd, dims), members in sorted(by.items())]


def _params(varcd: str, dims: tuple[str, ...], members: list[SeriesSpec]) -> dict:
    params = {"op": "2", "varcd": varcd, "lang": "PT", "Dim1": "T"}
    for dim in dims:
        codes = {dict(parse_native_code(s.native_code)[1])[dim] for s in members}
        params[dim] = ",".join(sorted(codes))
    return params


class INESource:
    name = "ine"
    expected_format = "json"

    def fetch(self, specs: list[SeriesSpec], http: Http) -> Iterator[RawResponse]:
        for varcd, dims, members in _groups(specs):
            params = _params(varcd, dims, members)
            r = http.get(BASE_URL, params=params)
            yield RawResponse(url=r.url, params=params, status=r.status, body=r.body)

    def parse(self, specs: list[SeriesSpec],
              responses: list[RawResponse]) -> dict[str, list[RawRow]]:
        groups = _groups(specs)
        if len(responses) != len(groups):
            raise ValueError(f"expected {len(groups)} INE responses (one per request), "
                             f"got {len(responses)}")
        out: dict[str, list[RawRow]] = {}
        for i, (resp, (varcd, dims, members)) in enumerate(zip(responses, groups)):
            cells = _cells(_load(resp.body, varcd), dims)
            for s in members:
                key = tuple(c for _, c in parse_native_code(s.native_code)[1])
                out[s.id] = [RawRow(period_raw=period, value_raw=value, flag_raw=flag,
                                    response_index=i)
                             for period, value, flag in cells.get(key, [])]
        return out


class _JsonNumber(str):
    """A bare JSON number. INE sends every value as a JSON string; a number where a string is
    expected is a format change (rejected by the `type(v) is str` checks below)."""


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        dup = sorted({k for k in keys if keys.count(k) > 1})
        raise ValueError(f"INE JSON object has duplicate keys {dup[:5]}")
    return dict(pairs)


def _load(body: bytes, varcd: str) -> dict:
    head = body[:64].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if head.startswith(b"<"):
        raise ValueError(f"INE answered markup, not JSON: {body[:80]!r}")
    try:
        doc = json.loads(body, parse_float=_JsonNumber, parse_int=_JsonNumber,
                         object_pairs_hook=_no_duplicate_keys)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"INE body is not valid JSON: {e}") from e
    if not (isinstance(doc, list) and len(doc) == 1 and isinstance(doc[0], dict)):
        raise ValueError("INE JSON must be a list holding one indicator record")
    rec = doc[0]
    status = rec.get("Sucesso")
    if not isinstance(status, dict) or "Verdadeiro" not in status or "Falso" in status:
        raise ValueError(f"INE error / unsuccessful answer: {status!r}")
    if rec.get("IndicadorCod") != varcd:
        raise ValueError(f"INE answered indicator {rec.get('IndicadorCod')!r}, asked {varcd!r}")
    dados = rec.get("Dados")
    if not isinstance(dados, dict) or not dados:
        raise ValueError("INE record has no 'Dados' periods")
    if rec.get("UltimoPref") not in dados:  # guard against a payload cut before the newest period
        raise ValueError(f"INE latest period {rec.get('UltimoPref')!r} missing from 'Dados'")
    return dados


def _cells(dados: dict, dims: tuple[str, ...]) -> dict[tuple[str, ...], list[tuple]]:
    """{(dim codes...): [(period label, valor | None, flag | None), ...]} in payload order."""
    fields = [_entry_field(d) for d in dims]
    expected_codes = set(fields)  # every non-period dimension of the indicator, pinned
    out: dict[tuple[str, ...], list[tuple]] = {}
    seen: set[tuple] = set()
    for period, entries in dados.items():
        if not isinstance(entries, list):
            raise ValueError(f"INE period {period!r}: expected a list of cells")
        for e in entries:
            if not isinstance(e, dict):
                raise ValueError(f"INE period {period!r}: cell is not an object")
            codes = {k for k in e if k == "geocod" or (k.startswith("dim_") and not k.endswith("_t"))}
            if codes != expected_codes:
                raise ValueError(f"INE cell dimensions {sorted(codes)} differ from native_code "
                                 f"dimensions {sorted(expected_codes)}")
            key = tuple(e[f] for f in fields)
            if not all(type(c) is str for c in key):
                raise ValueError(f"INE cell codes must be strings: {key!r}")
            if (period, key) in seen:
                raise ValueError(f"INE payload repeats cell {key} for {period!r}")
            seen.add((period, key))
            out.setdefault(key, []).append((period, *_value_and_flag(e, period)))
    return out


def _value_and_flag(e: dict, period: str) -> tuple[str | None, str | None]:
    value, shown = e.get("valor"), e.get("ind_string")
    sign, desc = e.get("sinal_conv"), e.get("sinal_conv_desc")
    for name, v in (("valor", value), ("ind_string", shown), ("sinal_conv", sign),
                    ("sinal_conv_desc", desc)):
        if v is not None and type(v) is not str:
            raise ValueError(f"INE {name} must be a JSON string, got {v!r} ({period})")
    if value is not None and not value.strip():
        raise ValueError(f"INE empty 'valor' for {period!r}")
    flag = map_ine_flag(sign, desc, value_present=value is not None)
    _check_rendering(value, shown, (sign or "").strip(), period)
    return value, flag


def _check_rendering(value: str | None, shown: str | None, sign: str, period: str) -> None:
    """`ind_string` is the published rendering of the same cell: '<number>[ <sign>]' with ','
    decimal and space thousands separators, or just the sign when there is no value."""
    if shown is None:
        raise ValueError(f"INE cell without 'ind_string' ({period})")
    text = shown.strip()
    if value is None:
        if text != sign:
            raise ValueError(f"INE cell without value shows {shown!r}, sign is {sign!r} ({period})")
        return
    if sign:
        if not text.endswith(" " + sign):
            raise ValueError(f"INE ind_string {shown!r} lacks its sign {sign!r} ({period})")
        text = text[: -len(sign) - 1]
    digits = text.replace(" ", "").replace(" ", "").replace(" ", "")
    try:
        same = Decimal(digits.replace(",", ".")) == Decimal(value) and "." not in digits
    except InvalidOperation:
        same = False
    if not same:
        raise ValueError(f"INE valor {value!r} and ind_string {shown!r} disagree ({period})")
