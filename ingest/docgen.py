"""Deterministic registry documentation; no source/verifier imports or operational I/O.

Channel descriptions below document reviewed implementations, not runtime registration,
current publisher availability, or legal permission beyond the registry's own policy.
"""
from collections import defaultdict
from html import escape
from pathlib import Path

import yaml

from ingest.models import SeriesSpec, SourceSpec
from ingest.registry import load_registry

# Documentation-only descriptions, reviewed against each verifier's module contract.
# Do not import adapters, verifiers, or parser helpers to populate this mapping.
_CHANNELS = {
    "bportugal": (
        "Collector: BPstat public JSON-stat API /data/v1/. Independent channel: "
        "portal JSON row records at https://bpstat.bportugal.pt/api/observations/ "
        "plus /api/series/?view_full=true metadata. Latest publication vintage is selected. "
        "No observation-status surface. Reviewed implementation: ingest/verifiers/bportugal.py."
    ),
    "eredes": (
        "Collector: OpenDataSoft explore v2.1 JSON records. Independent channel: "
        "https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
        "energia-produzida-total-nacional/exports/csv?lang=pt&timezone=UTC, "
        "one CSV per sampled UTC day, plus dataset metadata for units. "
        "Native quarter-hour timestamps are retained; no observation-status surface. "
        "Reviewed implementation: ingest/verifiers/eredes.py."
    ),
    "eurostat": (
        "Collector: Statistics API 1.0 JSON-stat. Independent channel: "
        "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/<dataset>/<key>"
        "?format=TSV (SDMX 2.1 TSV). Values and flags are read independently; unit identity "
        "is pinned by the native key, not a separate observed unit label. "
        "Reviewed implementation: ingest/verifiers/eurostat.py."
    ),
    "fred": (
        "Collector: keyed FRED JSON API. Independent channel: public server-rendered "
        "HTML data table https://fred.stlouisfed.org/data/<CODE>, including identity and "
        "unit metadata. No per-observation status surface. This is the reviewed table, "
        "not fredgraph.csv or the rounded landing page. "
        "Reviewed implementation: ingest/verifiers/fred.py."
    ),
    "ine": (
        "Collector: INE JSON Database API (valor token). Independent channel: "
        "https://www.ine.pt/bddXplorer/htdocs/bddXplorer04.jsp?indOcorrCod=<code>"
        "&contexto=bd&lang=PT, a server-rendered HTML table with Referer: https://www.ine.pt/ "
        "and xmlDocHidden period/dimension selection. Unit and conventional signs come "
        "from the table; Decimal comparison permits trailing-zero rendering differences. "
        "Reviewed implementation: ingest/verifiers/ine.py."
    ),
    "oecd": (
        "Collector: SDMX-JSON data 2.0. Independent channel: "
        "https://sdmx.oecd.org/public/rest/data/<agency>,<dataflow>/<key>"
        "?format=csvfilewithlabels&dimensionAtObservation=AllDimensions, "
        "labelled SDMX CSV on the same data API path with an independent parser. "
        "Dimensions, units, multiplier and status are checked from CSV fields. "
        "Reviewed implementation: ingest/verifiers/oecd.py."
    ),
    "ren": (
        "Collector: servicebus JSON API. Independent channel: "
        "https://datahub.ren.pt/service/exports/csv chart CSV export, "
        "modelId=1550 (balance) or modelId=2649 (market), scoped to a month. "
        "Balance CSV exposes GWh; market CSV has no unit annotation; neither exposes "
        "observation status. Reviewed implementation: ingest/verifiers/ren.py."
    ),
    "worldbank": (
        "Collector: API v2 JSON. Independent channel: publisher bulk CSV ZIP at "
        "https://api.worldbank.org/v2/<locale>/indicator/<CODE>?downloadformat=csv, "
        "including indicator and country metadata members. Reviewed locales: es for "
        "NY.GDP.MKTP.KD.ZG and SL.UEM.TOTL.ZS, en otherwise, with no automatic fallback. "
        "No per-cell unit/status surface. Reviewed implementation: ingest/verifiers/worldbank.py."
    ),
    "dgeg": (
        "Undocumented for current core definitions: no accepted exact independent channel "
        "and no ingest adapter/verifier. Partial APN/AEN PDF channels exist, but coverage, "
        "units, concepts and publication vintages remain unresolved. "
        "Scoped disposition and per-series evidence: registry/unmapped-dgeg.md."
    ),
}
_UNDOCUMENTED = "Undocumented: no reviewed independent channel is documented here."
_MARKDOWN_ENTITIES = str.maketrans({c: f"&#{ord(c)};" for c in "\\|`*_{}[]()#!~"})


def _cell(text: str) -> str:
    """Escape untrusted metadata as visible text, never Markdown/HTML/link syntax."""
    return (escape(text, quote=False).translate(_MARKDOWN_ENTITIES)
            .replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>"))


def render_sources(sources: list[SourceSpec], specs: list[SeriesSpec]) -> str:
    """Pure, order-independent Markdown renderer retaining every source and series."""
    by_source = defaultdict(list)
    for spec in specs:
        by_source[spec.source.name].append(spec)
    lines = [
        "# Sources and primary indicators",
        "",
        "Generated from the selected registry by `python -m ingest docs`. Do not edit by hand.",
        "Regenerate the committed catalogue: `python -m ingest docs > docs/data/sources.md`.",
        "Select another registry: `python -m ingest --registry PATH docs` (stdout only).",
        "",
        "This is registry policy and reviewed channel documentation, not a production status report.",
        "The core registry remains provisional pending owner review. Inactive definitions and",
        "cross-checks are retained below; a primary role does not imply active ingestion.",
        "Licence eligibility is the registry's redistribution_ok flag, not a new legal assessment.",
        "Serving also requires the pipeline's verification and row-eligibility gates.",
        "Channel descriptions document reviewed code, not a fresh endpoint check or independent",
        "verification of every unsampled observation. Unknown channels stay undocumented.",
        "",
    ]
    if not sources:
        lines.extend(["No source definitions.", ""])
    for source in sorted(sources, key=lambda s: s.name):
        rows = sorted(by_source[source.name], key=lambda s: s.id)
        active = sum(s.active for s in rows)
        allowed = str(source.redistribution_ok).lower()
        verifiable = str(source.verifiable).lower()
        eligibility = "allowed by registry" if source.redistribution_ok else "withheld by registry"
        lines.extend([
            f"## {_cell(source.name)}",
            "",
            f"Licence: {_cell(source.licence)}",
            f"Licence URL: {_cell(source.licence_url)}",
            f"Attribution: {_cell(source.attribution)}",
            f"Licence eligibility: {eligibility} (redistribution_ok={allowed}).",
            f"Independent verification policy: verifiable={verifiable}.",
            f"Registry entries: {len(rows)} ({active} active, {len(rows) - active} inactive).",
            "",
            "Independent verification channel: " + _cell(_CHANNELS.get(source.name, _UNDOCUMENTED)),
            "",
        ])
        if not rows:
            lines.extend(["No series defined.", ""])
            continue
        lines.extend([
            "Exact primary-series identifiers and indicator keys, with cross-checks labelled separately:",
            "",
            "| Series ID | Indicator key | Role | State | Native code |",
            "|---|---|---|---|---|",
        ])
        for spec in rows:
            cells = [spec.id, spec.indicator_key, spec.role, "active" if spec.active else "inactive",
                     spec.native_code if spec.native_code is not None else "Not specified"]
            lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_sources(registry: Path) -> str:
    """Read a registry without changing load_registry's public series-list contract.

    Read source definitions separately because the ingestion loader intentionally returns
    series only, which cannot represent sources with zero series. Validate empty sources
    with the same SourceSpec model and retain the existing series/primary validation.
    """
    doc = yaml.safe_load(Path(registry).read_text(encoding="utf-8")) or {}
    sources = [SourceSpec(name=name, **(body or {}))
               for name, body in (doc.get("sources") or {}).items()]
    return render_sources(sources, load_registry(registry))
