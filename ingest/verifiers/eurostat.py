"""Independent verifier for Eurostat (spec 6b) through a DIFFERENT channel than the collector:

    collector:  Statistics API 1.0, JSON-stat 2.0  (.../statistics/1.0/data/<dataset>?<dim>=..)
    verifier:   SDMX 2.1 REST data API, TSV format (.../sdmx/2.1/data/<dataset>/<key>?format=TSV)

Different endpoint, different query language (SDMX dotted key vs query parameters), different
format (Eurostat's tab-separated bulk-download layout: one row per series, one column per period,
value and flags in one cell like '12.3 p' or ': c') and a separate parser written here. It shares
no code with ingest/sources/eurostat.py: the tiny native_code parsing and the flag-vocabulary
table below are DUPLICATED ON PURPOSE (a shared helper would be shared parsing code, which
register_verifier and the independence guard forbid); if the two copies ever disagree,
verification fails loudly instead of both sides agreeing on the same mistake.

One request per (dataset, non-geo key) group of the sampled items, all geos of the group joined
with '+', full history (no period bounds, so one fixed document per group). Every ItemResult of a
group carries that TSV as `evidence`.

Exposed per item: the value token (observed_text, '.' decimal, flag letters stripped), the status
flag mapped onto the shared vocabulary (observed_flag; 'normal' when the cell has no flag).
observed_unit is NOT exposed (None): the TSV shows the unit only as the code that is part of the
requested key; the row is accepted only if its unit code equals the one pinned in native_code, and
the code <-> registry-label pairing was checked when the registry was mapped.

Registration: the CLI (Task 17) calls register_verifier(EurostatVerifier()); this module cannot
(register_verifier is not in the verifier import allowlist).
"""
import csv
import io

from ingest.http import Http, HttpResult
from ingest.verifiers import BlindItem, ItemResult

SDMX_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"

# Duplicate of ingest/flags.py's Eurostat mapping, on purpose (see module docstring).
_FLAG_OF = {"b": "break", "d": "break", "p": "provisional", "e": "estimated", "s": "estimated",
            "f": "estimated", "u": "estimated", "n": "estimated", "i": "estimated",
            "r": "revised"}
_STRONGEST_FIRST = ("break", "provisional", "estimated", "revised")
_NO_VALUE = frozenset({"c", "z"})
# Duplicate of ingest/flags.py's EUROSTAT_CONFIDENTIALITY, on purpose. The TSV renders the
# JSON-stat status '|C' as ': @C': a cell with one of these has no publishable value.
_CONFIDENTIALITY = frozenset({"C", "N"})  # confidential, not for publication


def _key(native_code: str | None) -> tuple[str, list[tuple[str, str]]]:
    """Duplicate of the source's native_code parsing, on purpose (see module docstring)."""
    dataset, sep, rest = (native_code or "").partition(":")
    pairs = [tuple(p.split("=")) for p in rest.split(",")] if rest else []
    if not (dataset and sep) or any(len(p) != 2 or not all(p) for p in pairs):
        raise ValueError(f"bad Eurostat native_code {native_code!r}")
    if "geo" not in {d for d, _ in pairs}:
        raise ValueError(f"Eurostat native_code without geo: {native_code!r}")
    return dataset, pairs


def _vocabulary(letters: str) -> str:
    unknown = sorted(set(letters) - set(_FLAG_OF))
    if unknown:
        raise ValueError(f"unknown Eurostat flag(s) {unknown} on a published value")
    found = {_FLAG_OF[c] for c in letters}
    for flag in _STRONGEST_FIRST:
        if flag in found:
            return flag
    return "normal"


def _cell(text: str) -> tuple[str | None, str]:
    """'12.3 p' -> ('12.3', 'p'); ': c' -> (None, 'c'); '6.0 ' -> ('6.0', '');
    ': @C' -> (None, '') (confidential: no publishable value)."""
    parts = text.split()
    if not parts:
        return None, ""
    letters, at, conf = "".join(parts[1:]).partition("@")
    if at and conf not in _CONFIDENTIALITY:
        raise ValueError(f"unknown Eurostat confidentiality code in {text!r}")
    if set(letters) - _NO_VALUE - set(_FLAG_OF):
        raise ValueError(f"unknown Eurostat flag in {text!r}")
    token = parts[0]
    if token == ":" or at:
        return None, letters
    if not token[0].isdigit() and token[0] not in "+-.":
        raise ValueError(f"unexpected TSV cell {text!r}")
    return token, letters


def _table(body: bytes) -> tuple[list[str], dict[tuple[str, ...], dict[str, str]]]:
    """Eurostat TSV -> (dimension names, {key codes: {period: cell text}})."""
    text = body.decode("utf-8-sig")
    if text.lstrip()[:1] in ("<", "{"):
        raise ValueError(f"Eurostat SDMX answered markup/JSON, not TSV: {text[:80]!r}")
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    header = next(reader, None)
    if not header or "\\" not in header[0]:
        raise ValueError(f"not a Eurostat TSV header: {header!r}")
    dims_part, _, time_name = header[0].partition("\\")
    if time_name.strip() != "TIME_PERIOD":
        raise ValueError(f"unexpected TSV time header {header[0]!r}")
    dims = dims_part.split(",")
    periods = [h.strip() for h in header[1:]]
    rows: dict[tuple[str, ...], dict[str, str]] = {}
    for line in reader:
        if not line:
            continue
        codes = tuple(line[0].split(","))
        if len(codes) != len(dims) or len(line) - 1 != len(periods):
            raise ValueError(f"malformed TSV row {line[:2]!r}")
        cells = dict(zip(periods, line[1:]))
        if codes in rows and rows[codes] != cells:
            raise ValueError(f"TSV has conflicting rows for series {line[0]!r}")
        rows[codes] = cells
    return dims, rows


class EurostatVerifier:
    source_name = "eurostat"

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]:
        groups: dict[tuple, list[int]] = {}
        keys = []
        for n, item in enumerate(items):
            dataset, pairs = _key(item.spec.native_code)
            keys.append((dataset, pairs))
            rest = tuple((d, c) if d != "geo" else ("geo", "*") for d, c in pairs)
            groups.setdefault((dataset, rest), []).append(n)

        results: list[ItemResult | None] = [None] * len(items)
        for (dataset, rest), members in groups.items():
            geos = sorted({dict(keys[n][1])["geo"] for n in members})
            sdmx_key = ".".join("+".join(geos) if d == "geo" else c for d, c in rest)
            r = http.get(f"{SDMX_URL}{dataset}/{sdmx_key}", params={"format": "TSV"})
            if not 200 <= r.status < 300:
                raise ValueError(f"Eurostat SDMX {r.url} answered HTTP {r.status}")
            dims, rows = _table(r.body)
            for n in members:
                results[n] = self._one(items[n], dict(keys[n][1]), dims, rows, r)
        return results

    @staticmethod
    def _one(item: BlindItem, pinned: dict[str, str], dims: list[str],
             rows: dict[tuple[str, ...], dict[str, str]], r: HttpResult) -> ItemResult:
        if set(dims) != set(pinned):
            raise ValueError(f"TSV dimensions {dims} differ from native_code {sorted(pinned)}")
        row = rows.get(tuple(pinned[d] for d in dims))  # includes the pinned unit code
        cell = row.get(item.period) if row is not None else None
        text, letters = _cell(cell) if cell is not None else (None, "")
        flag = _vocabulary(letters) if text is not None else None
        return ItemResult(series_id=item.series_id, period=item.period, observed_text=text,
                          evidence_url=r.url, observed_decimal=".", observed_unit=None,
                          observed_flag=flag, evidence=r.body)
