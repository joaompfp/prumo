"""Propose the core indicator registry from the legacy export (Task 8, Ruling T).

Reads the legacy CSV once and writes, into `out_dir`:
  core.proposed.yaml (+ an identical core.yaml)  the provisional core set, in `ingest.registry` format
  overlaps.md        indicators published by more than one series, the proposed primary and why
  deferred-tail.md   known series left out of core (long tail, non-core theme or geography)
  unclassified.md    series left out because the data cannot support a registry row as-is
  licences-todo.md   sources whose licence the builder could not confirm

Every judgement is in the explicit tables below; values are compared as Decimal, never float.
"""
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

from ingest.legacy_import import fetched_at_utc, legacy_geography, legacy_series_id
from ingest.models import normalize_period, parse_decimal

PROVISIONAL = "# PROVISIONAL — owner review pending"
LARGE_GAP = Decimal("0.02")  # relative primary-vs-cross-check gap flagged in overlaps.md

# --- geography and primary-source rule (spec §5) ------------------------------------------------

PT_GEOS = {"PT", "Continente"}
EUROPE = {"EU", "EU27", "EU27_2020", "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "GR",
          "ES", "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "RO", "SE",
          "SI", "SK", "GB", "NO", "CH"}
PT_INSTITUTIONS = ("INE", "BPORTUGAL", "REN", "DGEG", "ERSE")
_ORDER_PT = PT_INSTITUTIONS + ("EUROSTAT", "OECD", "WORLDBANK", "FRED")
_ORDER_EUROPE = ("EUROSTAT", "OECD", "WORLDBANK", "FRED") + PT_INSTITUTIONS
_ORDER_WORLD = ("WORLDBANK", "OECD", "FRED", "EUROSTAT") + PT_INSTITUTIONS
_RULE_TEXT = {"pt": "Portuguese institution for Portuguese data",
              "europe": "Eurostat first for European geography",
              "world": "World Bank / OECD / FRED for world data"}


def _geo_class(geography: str) -> str:
    return "pt" if geography in PT_GEOS else "europe" if geography in EUROPE else "world"


def _rank(source: str, geography: str) -> int:
    order = {"pt": _ORDER_PT, "europe": _ORDER_EUROPE, "world": _ORDER_WORLD}[_geo_class(geography)]
    return order.index(source) if source in order else len(order)


def _core_geography(source: str, geography: str) -> bool:
    return source == "WORLDBANK" or geography in PT_GEOS | EUROPE | {"WORLD"}


# --- theme by legacy indicator name ---------------------------------------------------------------

THEMES = {
    "economy": {
        # Banco de Portugal
        "credit_consumer", "credit_housing", "de_10y", "deposits", "eur_usd", "euribor_12m",
        "euribor_1m", "euribor_3m", "euribor_6m", "pt_10y", "spread_pt_de",
        # Eurostat
        "cci", "chemicals_pharma", "construction_index", "construction_output", "consumer_confidence",
        "current_account_pct_gdp", "earn_ses_pub2s", "employment_rate", "gdp_per_capita_eur",
        "gdp_per_capita_pps", "gdp_quarterly", "gov_debt_pct_gdp", "gov_deficit_pct_gdp", "hicp",
        "hourly_labour_cost_index", "inflation", "ipi", "machinery", "manufacturing", "metals",
        "price_level_index", "rubber_plastics", "total_industry", "transport_eq", "unemployment",
        "unemployment_m",
        # FRED (IMF primary commodity prices)
        "aluminum", "coffee", "copper", "corn", "cotton", "iron_ore", "nickel", "soybean", "steel",
        "sugar", "wheat", "zinc",
        # INE
        "conf_manufacturing", "emp_industry_cae", "exports_monthly", "gdp_yoy", "hicp_yoy",
        "imports_monthly", "ipc_yoy", "wages_industry_cae",
        # OECD
        "cli", "employment", "order_books", "production", "selling_prices", "unemp_m",
        # World Bank
        "exports", "exports_pct_gdp", "fdi_inflows_pct_gdp", "female_labor_participation", "gdp",
        "gdp_growth", "gdp_per_capita", "gdp_per_capita_ppp", "gdp_usd", "gini",
        "gov_debt_pct_gdp_wb", "imports", "imports_pct_gdp", "labor_force", "rnd_pct_gdp",
        "trade_balance", "trade_balance_pct_gdp", "unemployment_wb",
    },
    "demography": {"birth_rate", "death_rate", "life_expectancy", "population", "urbanization"},
    "energy": {"brent_oil", "natural_gas", "energy_use"},
}
THEME_PREFIXES = (("ipi_", "economy"), ("STS_INPR_", "economy"), ("labour_productivity_", "economy"),
                  ("unit_labour_cost", "economy"), ("commodity_", "economy"),
                  ("electricity", "energy"), ("access_", "energy"), ("tariff_", "energy"),
                  ("btn_", "energy"))
# Known indicators whose theme is outside the core three (spec §4): deferred, not unclassified.
NON_CORE_THEMES = {"health_expenditure": "health", "literacy_rate": "education",
                   "school_enrollment_secondary": "education", "tertiary_enrollment": "education",
                   "internet_users_pct": "digital"}
# DGEG: only the national headline energy indicators are core; the rest is the long tail.
DGEG_CORE = {"co2_emissions_energy", "co2_emissions_total", "consumption_industry",
             "consumption_primary_total", "consumption_transport", "electricity_consumption",
             "energy_dependence", "energy_intensity", "energy_intensity_final",
             "energy_intensity_industry", "energy_intensity_primary", "energy_intensity_services",
             "final_energy_consumption", "primary_energy_consumption", "renewable_share_electricity",
             "renewable_share_total", "renewable_share_transport"}

# Legacy names that publish the same quantity (everything else is its own concept). Checked against
# the data: World Bank GC.DOD.TOTL.GD.ZS is central-government debt, so it is NOT Eurostat's
# general-government gov_debt_pct_gdp; FRED commodity_cotton is cotton / 100 (see LEGACY_DATA_PROBLEMS).
CONCEPTS = {
    ("EUROSTAT", "unemployment"): "unemployment_rate", ("OECD", "unemp_m"): "unemployment_rate",
    ("INE", "unemployment"): "unemployment_rate", ("WORLDBANK", "unemployment_wb"): "unemployment_rate",
    ("WORLDBANK", "unemployment"): "unemployment_rate",
    ("EUROSTAT", "cci"): "consumer_confidence", ("EUROSTAT", "consumer_confidence"): "consumer_confidence",
    ("INE", "hicp_yoy"): "hicp_yoy", ("EUROSTAT", "inflation"): "hicp_yoy",
    ("EUROSTAT", "ipi"): "ipi_total", ("EUROSTAT", "total_industry"): "ipi_total",
    ("EUROSTAT", "STS_INPR_M_BD"): "ipi_total", ("INE", "ipi_seasonal_cae_TOT"): "ipi_total",
    ("EUROSTAT", "manufacturing"): "ipi_manufacturing", ("EUROSTAT", "STS_INPR_M_C"): "ipi_manufacturing",
    ("INE", "ipi_seasonal_cae_C"): "ipi_manufacturing",
    ("EUROSTAT", "chemicals_pharma"): "ipi_c20_c21", ("EUROSTAT", "STS_INPR_M_C20C21"): "ipi_c20_c21",
    ("EUROSTAT", "transport_eq"): "ipi_c29_c30", ("EUROSTAT", "STS_INPR_M_C29C30"): "ipi_c29_c30",
    ("EUROSTAT", "rubber_plastics"): "ipi_c22", ("INE", "ipi_seasonal_cae_22"): "ipi_c22",
    ("EUROSTAT", "machinery"): "ipi_c28", ("INE", "ipi_seasonal_cae_28"): "ipi_c28",
    **{("FRED", n): f"{n}_price" for n in ("iron_ore", "nickel", "soybean", "steel", "sugar", "zinc")},
    **{("FRED", f"commodity_{n}"): f"{n}_price"
       for n in ("iron_ore", "nickel", "soybean", "steel", "sugar", "zinc")},
}
# Legacy series whose stored unit label or values cannot be trusted as-is (found by inspection).
LEGACY_DATA_PROBLEMS = {
    ("EUROSTAT", "unemployment_m"): "unit label PC_ACT, but values are thousands of persons "
                                    "(detail: ei_lmhu_m LM-UN-T-TOT)",
    ("INE", "emp_industry_cae"): "unit label %, but values are an index (about 100)",
    ("FRED", "commodity_cotton"): "values are fred.cotton / 100 (legacy-derived, not a publisher figure)",
}


def _concept(source: str, indicator: str) -> str:
    """Shared concept from CONCEPTS; otherwise source-qualified, so two sources that happen to use
    the same legacy name for different definitions (e.g. employment_rate) never merge."""
    return CONCEPTS.get((source, indicator)) or f"{source.lower()}_{indicator}"

# --- licences (spec §11.4): only what was confirmed; everything else is UNVERIFIED ------------------

UNVERIFIED = "UNVERIFIED — builder must confirm before serving"
LICENCES = {
    "eurostat": dict(licence="CC BY 4.0",
                     licence_url="https://ec.europa.eu/eurostat/web/main/help/copyright-notice",
                     attribution="Source: Eurostat", redistribution_ok=True),
    "worldbank": dict(licence="CC BY 4.0", licence_url="https://datacatalog.worldbank.org/public-licenses",
                      attribution="Source: World Bank", redistribution_ok=True),
}
# source -> (url to check, attribution, why unconfirmed)
LICENCE_TODO = {
    "ine": ("https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_condicoes_utilizacao",
            "Source: INE — Statistics Portugal",
            "Believed free reuse with attribution; page was 'em manutenção' when checked (2026-11-11)."),
    "bportugal": ("https://bpstat.bportugal.pt/", "Source: Banco de Portugal (BPstat)",
                  "BPstat terms of use not read."),
    "ren": ("https://www.ren.pt/", "Source: REN — Redes Energéticas Nacionais",
            "REN data-hub terms not read."),
    "dgeg": ("https://www.dgeg.gov.pt/", "Source: DGEG",
             "Published via dados.gov.pt; licence is stated per dataset, not checked."),
    "erse": ("https://www.erse.pt/", "Source: ERSE", "ERSE terms not read."),
    "oecd": ("https://www.oecd.org/termsandconditions/", "Source: OECD",
             "Believed CC BY 4.0 since 2024; terms page returned HTTP 403 when checked."),
    "fred": ("https://fred.stlouisfed.org/docs/api/terms_of_use.html",
             "Source: IMF Primary Commodity Prices, via FRED (Federal Reserve Bank of St. Louis)",
             "FRED terms defer to each series' owner; these series are IMF data, IMF terms not read."),
}


def _source_spec(name: str) -> dict:
    if name in LICENCES:
        return LICENCES[name]
    url, attribution, _ = LICENCE_TODO[name]
    return dict(licence=UNVERIFIED, licence_url=url, attribution=attribution, redistribution_ok=False)


def _theme(indicator: str) -> str | None:
    if indicator in DGEG_CORE:
        return "energy"
    for theme, names in THEMES.items():
        if indicator in names:
            return theme
    return next((t for p, t in THEME_PREFIXES if indicator.startswith(p)), None)


# --- reading the export ------------------------------------------------------------------------

def _row_frequency(period: str) -> tuple[str, str] | None:
    for f in "ASQMD":
        try:
            return f, normalize_period(period, f)
        except ValueError:
            continue
    return None


@dataclass
class _Series:
    id: str
    source: str
    indicator: str
    geography: str
    n: int = 0
    units: Counter = field(default_factory=Counter)  # non-empty unit -> rows
    n_no_unit: int = 0
    unitless_periods: list = field(default_factory=list)  # periods of blank-unit rows
    freqs: Counter = field(default_factory=Counter)
    codes: Counter = field(default_factory=Counter)
    # normalized period -> (fetched_at, value text), latest vintage among rows WITH an explicit unit:
    # blank-unit rows are quarantined on import (Ruling V), so they never stand for the series.
    latest: dict = field(default_factory=dict)

    def add(self, r: dict) -> None:
        self.n += 1
        has_unit = bool(r["unit"].strip())
        if r["source_id"]:
            self.codes[r["source_id"]] += 1
        fp = _row_frequency(r["period"])
        if has_unit:
            self.units[r["unit"].strip()] += 1
        else:
            self.n_no_unit += 1
            self.unitless_periods.append(fp[1] if fp else r["period"])
        if fp:
            self.freqs[fp[0]] += 1
        if fp and has_unit:
            fetched = fetched_at_utc(r["fetched_at"])
            if fp[1] not in self.latest or self.latest[fp[1]][0] <= fetched:
                self.latest[fp[1]] = (fetched, r["value"])

    @property
    def n_explicit(self) -> int:
        return self.n - self.n_no_unit

    @property
    def frequency(self) -> str:
        return next(iter(self.freqs))

    @property
    def last_period(self) -> str:
        return max(self.latest) if self.latest else ""


def _read(csv_path: Path) -> tuple[dict[str, _Series], int]:
    series: dict[str, _Series] = {}
    n = 0
    with Path(csv_path).open(newline="") as f:
        for r in csv.DictReader(f):
            n += 1
            sid = legacy_series_id(r["source"], r["indicator"], r["region"])
            if sid not in series:
                series[sid] = _Series(sid, r["source"], r["indicator"],
                                      legacy_geography(r["source"], r["region"]))
            series[sid].add(r)
    return series, n


def _classify(s: _Series) -> tuple[str, str]:
    """('core' | 'deferred' | 'unclassified', reason)."""
    if s.source == "DGEG" and s.indicator not in DGEG_CORE:
        return "deferred", "DGEG long tail (fuel, price, plant and regional series)"
    if s.indicator in NON_CORE_THEMES:
        return "deferred", f"theme not core ({NON_CORE_THEMES[s.indicator]})"
    if _theme(s.indicator) is None:
        return "unclassified", "no theme mapping"
    if (s.source, s.indicator) in LEGACY_DATA_PROBLEMS:
        return "unclassified", "legacy data problem: " + LEGACY_DATA_PROBLEMS[(s.source, s.indicator)]
    if not _core_geography(s.source, s.geography):
        return "deferred", "geography outside core"
    if not s.units:
        return "unclassified", "no unit in the legacy data"
    if len(s.units) > 1:
        return "unclassified", "several units: " + " | ".join(sorted(s.units))
    if not s.freqs:
        return "unclassified", "no parseable period"
    if len(s.freqs) > 1:
        return "unclassified", "several period formats: " + ", ".join(sorted(s.freqs))
    if s.frequency == "M" and s.n >= 4 and {p[5:] for p in s.latest} <= {"01", "04", "07", "10"}:
        return "unclassified", "quarterly data stored as months"
    return "core", ""


# --- comparison --------------------------------------------------------------------------------

def _dec(text: str) -> Decimal | None:
    try:
        return parse_decimal(text, ".")
    except (ValueError, InvalidOperation):
        return None


def _gap(primary: _Series, other: _Series) -> tuple[int, int, Decimal | None]:
    """(overlapping periods, exactly equal, max relative gap) on the latest legacy vintage, over
    rows with an explicit unit only (a core series has exactly one, its registry unit)."""
    n = equal = 0
    worst: Decimal | None = None
    for period in primary.latest.keys() & other.latest.keys():
        a, b = _dec(primary.latest[period][1]), _dec(other.latest[period][1])
        if a is None or b is None:
            continue
        n += 1
        equal += a == b
        scale = max(abs(a), abs(b))
        rel = abs(a - b) / scale if scale else Decimal(0)
        worst = rel if worst is None else max(worst, rel)
    return n, equal, worst


# --- output ------------------------------------------------------------------------------------

def _table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def propose(csv_path: Path, out_dir: Path, *, force: bool = False) -> None:
    """Write the proposal into `out_dir`. Refuses (FileExistsError) when `out_dir/core.yaml`
    already carries `native_code` entries (hand-curated source mappings since Task 9, which a
    regeneration would drop) unless force=True."""
    existing = Path(out_dir) / "core.yaml"
    if not force and existing.exists() and "native_code:" in existing.read_text():
        raise FileExistsError(f"{existing} contains native_code entries (curated source mappings);"
                              " regenerating would drop them. Pass force=True to overwrite.")
    series, n_rows = _read(csv_path)
    buckets: dict[str, list[tuple[_Series, str]]] = defaultdict(list)
    for s in series.values():
        bucket, reason = _classify(s)
        buckets[bucket].append((s, reason))

    groups: dict[str, list[_Series]] = defaultdict(list)
    for s, _ in buckets["core"]:
        concept = _concept(s.source, s.indicator)
        groups[f"{concept}.{s.geography}.{s.frequency}"].append(s)

    rows, overlaps = [], []
    for key in sorted(groups):
        members = sorted(groups[key], key=lambda s: (_rank(s.source, s.geography), -s.n_explicit,
                                                     -len(s.latest), s.id))
        primary = members[0]
        for s in members:
            code = next(iter(s.codes)) if len(s.codes) == 1 else None
            row = {"id": s.id, "source": s.source.lower(), "indicator_key": key,
                   "role": "primary" if s is primary else "cross_check",
                   "theme": _theme(s.indicator), "geography": s.geography,
                   "frequency": s.frequency, "unit": next(iter(s.units)), "decimal": "."}
            if code:
                row["native_code"] = code
            rows.append(row)
        if len(members) > 1:
            overlaps.append((key, primary, members))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    used = sorted({r["source"] for r in rows})
    doc = {"sources": {name: _source_spec(name) for name in used}, "series": rows}
    text = (f"{PROVISIONAL}\n# Generated by ingest/propose_registry.py from the legacy export; "
            "see overlaps.md, deferred-tail.md, unclassified.md, licences-todo.md.\n"
            + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120))
    (out / "core.proposed.yaml").write_text(text)
    (out / "core.yaml").write_text(text)
    (out / "overlaps.md").write_text(_overlaps_md(overlaps))
    (out / "deferred-tail.md").write_text(_deferred_md(buckets["deferred"], n_rows))
    (out / "unclassified.md").write_text(_unclassified_md(buckets["unclassified"], buckets["core"]))
    (out / "licences-todo.md").write_text(_licences_md(used))


def _why(primary: _Series, members: list[_Series]) -> str:
    """The reason that actually decided the primary (rank rule, then the same-source tie-break)."""
    others = [m for m in members if m is not primary]
    other_sources = sorted({m.source for m in others if m.source != primary.source})
    same = [m for m in others if m.source == primary.source]
    parts = []
    if other_sources:
        cls = _geo_class(primary.geography)
        if cls == "pt" and primary.source in PT_INSTITUTIONS:
            parts.append(_RULE_TEXT["pt"])
        elif cls == "europe" and primary.source == "EUROSTAT":
            parts.append(_RULE_TEXT["europe"])
        elif cls == "world" and primary.source in ("WORLDBANK", "OECD", "FRED"):
            parts.append(_RULE_TEXT["world"])
        else:
            parts.append(f"closest to origin by source rank: {primary.source} ahead of "
                         + ", ".join(other_sources))
    if same:
        counts = f"{primary.n_explicit} vs " + ", ".join(str(m.n_explicit) for m in same)
        decided = ("by row count" if all(m.n_explicit < primary.n_explicit for m in same)
                   else "by period count, then series id (equal row counts)")
        parts.append(f"same quantity under {len(same) + 1} {primary.source} legacy names; "
                     f"tie broken {decided} ({counts})")
    return "; ".join(parts)


def _overlaps_md(overlaps: list) -> str:
    rows = []
    n_large = 0
    for key, primary, members in overlaps:
        for s in members[1:]:
            n, equal, worst = _gap(primary, s)
            large = worst is not None and worst > LARGE_GAP
            n_large += large
            rows.append([key, primary.id, _why(primary, members),
                         f"{primary.n_explicit} / {primary.last_period}", s.id,
                         f"{s.n_explicit} / {s.last_period}",
                         f"{next(iter(primary.units))} vs {next(iter(s.units))}", n, equal,
                         "—" if worst is None else f"{(worst * 100).quantize(Decimal('0.01'))}%",
                         "LARGE" if large else ""])
    return (f"{PROVISIONAL}\n\n# Overlapping indicators\n\n"
            + _table(["indicators", "cross-checks", "large gaps"],
                     [[len(overlaps), len(rows), n_large]])
            + "\n" + _table(["indicator_key", "primary", "why", "primary rows / latest", "cross_check",
                             "rows / latest", "units", "common periods", "equal", "max rel. gap",
                             f"flag (> {LARGE_GAP * 100}%)"], rows)
            + "\nGaps compare the latest legacy vintage per period, as exact decimals, over periods "
              "where BOTH series' legacy rows carry an explicit unit (the proposed one). Rows with a "
              "blank unit are excluded: they can be another base-year vintage (Ruling V) and are "
              "quarantined as missing_unit on import, never imported. Row counts are explicit-unit "
              "rows. A large gap is "
              "a review flag, never auto-corrected (spec §5). Units are shown as the legacy data "
              "labels them; differing labels can mean the same unit.\n")


def _deferred_md(items: list, n_rows: int) -> str:
    fam: dict[tuple, list] = defaultdict(lambda: [0, 0])
    per_source: dict[str, list] = defaultdict(lambda: [0, 0])
    for s, reason in items:
        fam[(s.source, s.indicator, reason)][0] += 1
        fam[(s.source, s.indicator, reason)][1] += s.n
        per_source[s.source][0] += 1
        per_source[s.source][1] += s.n
    return (f"{PROVISIONAL}\n\n# Deferred tail (left out of core)\n\n"
            + _table(["source", "series", "rows"],
                     [[k, *v] for k, v in sorted(per_source.items())]
                     + [["total", len(items), f"{sum(s.n for s, _ in items)} of {n_rows}"]])
            + "\n" + _table(["source", "indicator family", "reason", "series", "rows"],
                            [[s, i, r, *v] for (s, i, r), v in sorted(fam.items())])
            + "\nKnown series kept out of the core set (spec §4); they can be added to the registry "
              "once the pipeline has proven itself.\n")


def _unclassified_md(items: list, core: list) -> str:
    by_reason = Counter(r.split(":")[0] for _, r in items)
    unitless = [(s, "core: these rows quarantined as missing_unit") for s, _ in core if s.n_no_unit]
    unitless += [(s, "not core: no row has a unit") for s, r in items if not s.units]
    return (f"{PROVISIONAL}\n\n# Unclassified (left out of core)\n\n"
            + _table(["reason", "series"], sorted(by_reason.items()))
            + "\n" + _table(["source", "indicator", "geography", "rows", "reason"],
                            [[s.source, s.indicator, s.geography, s.n, r]
                             for s, r in sorted(items, key=lambda t: t[0].id)])
            + "\nThe legacy data cannot support a registry row for these as-is (unit or frequency "
              "unknown or inconsistent, or no theme mapping). The source adapter task that owns each "
              "one can add it with the unit and frequency taken from the publisher's metadata.\n"
            + "\n## Legacy rows quarantined: unit missing\n\n"
              "Legacy rows with a blank unit are never given the registry unit (Ruling V): for core "
              "series they are quarantined as `missing_unit` on import; series with no unit at all "
              "are not core. Nothing here is imported.\n\n"
            + _table(["series", "status", "registry unit", "rows with unit", "rows without unit",
                      "periods without unit"],
                     [[s.id, status, next(iter(s.units)) if len(s.units) == 1 else "—",
                       s.n_explicit, s.n_no_unit,
                       f"{min(s.unitless_periods)} .. {max(s.unitless_periods)}"]
                      for s, status in sorted(unitless, key=lambda t: t[0].id)]))


def _licences_md(used: list[str]) -> str:
    todo = [[n, LICENCE_TODO[n][0], LICENCE_TODO[n][2]] for n in used if n not in LICENCES]
    return (f"{PROVISIONAL}\n\n# Licences to confirm\n\n"
            + _table(["source", "terms to check", "status"], todo)
            + f"\nThese sources carry `licence: \"{UNVERIFIED}\"` and `redistribution_ok: false` in "
              "the registry: nothing from them may be served until a person confirms the terms "
              "(spec §11.4). Confirmed: "
            + ", ".join(f"{n} ({LICENCES[n]['licence']})" for n in used if n in LICENCES) + ".\n")
