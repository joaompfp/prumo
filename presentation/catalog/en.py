"""English reader text. Titles are keyed by derived series key."""

FORMULAS = {
    "period_change": "Change from the previous period (difference), calculated by Prumo "
                     "from {base}",
    "period_change_pct": "Change from the previous period (%), calculated by Prumo "
                         "from {base}",
    "yoy_change": "Year-on-year change (difference), calculated by Prumo from {base}",
    "yoy_change_pct": "Year-on-year change (%), calculated by Prumo from {base}",
    "rebase_100": "Rebased index ({base_period} = 100), calculated by Prumo from {base}",
}

UNITS = {
    "pct": "%",
    "pp": "p.p.",
    "balance": "balance",
    "index_2015_100": "index 2015=100",
}

CAVEATS = {
    "sa_base": "Calculated by Prumo on the seasonally adjusted series; "
               "it is not the publisher's official rate.",
    "stock_base": "Calculated by Prumo on stock (outstanding) amounts; "
                  "it is not the publisher's official rate.",
}

ATTRIBUTION_SUFFIX = "Calculated by Prumo"

_IPI = "Industrial production index"
_YOY = "year-on-year change (%)"
TITLES = {
    "derived.ipi_seasonal_cae_TOT.PT.yoy_change_pct": f"{_IPI}, total — {_YOY}",
    "derived.ipi_seasonal_cae_TOT.PT.period_change_pct":
        f"{_IPI}, total — change from the previous period (%)",
    "derived.ipi_seasonal_cae_B.PT.yoy_change_pct": f"{_IPI}, mining and quarrying — {_YOY}",
    "derived.ipi_seasonal_cae_C.PT.yoy_change_pct": f"{_IPI}, manufacturing — {_YOY}",
    "derived.ipi_seasonal_cae_D.PT.yoy_change_pct":
        f"{_IPI}, electricity, gas and steam — {_YOY}",
    "derived.ipi_seasonal_cae_E.PT.yoy_change_pct":
        f"{_IPI}, water supply, sewerage and waste — {_YOY}",
    "derived.exports_monthly.PT.yoy_change_pct": f"Exports of goods — {_YOY}",
    "derived.imports_monthly.PT.yoy_change_pct": f"Imports of goods — {_YOY}",
    "derived.credit_housing.PT.yoy_change_pct": f"Housing loans — {_YOY}",
    "derived.credit_consumer.PT.yoy_change_pct": f"Consumer credit — {_YOY}",
    "derived.deposits_households.PT.yoy_change_pct": f"Household deposits — {_YOY}",
    "derived.metals.PT.yoy_change_pct":
        f"Industrial production, metals and metal products — {_YOY}",
    "derived.chemicals_pharma.PT.yoy_change_pct":
        f"Industrial production, chemicals and pharmaceuticals — {_YOY}",
    "derived.population.PT.yoy_change_pct": f"Resident population — {_YOY}",
    "derived.live_births.PT.yoy_change_pct": f"Live births — {_YOY}",
    "derived.deaths.PT.yoy_change_pct": f"Deaths — {_YOY}",
    "derived.gdp_per_capita_eur.PT.yoy_change_pct": f"GDP per capita — {_YOY}",
    "derived.unemployment_monthly.PT.period_change":
        "Unemployment rate — change from the previous period (p.p.)",
    "derived.unemployment_monthly.PT.yoy_change":
        "Unemployment rate — year-on-year change (p.p.)",
    "derived.pt_10y.PT.period_change":
        "10-year government bond yield — change from the previous period (p.p.)",
    "derived.pt_10y.PT.yoy_change": "10-year government bond yield — year-on-year change (p.p.)",
    "derived.cci.PT.period_change":
        "Consumer confidence indicator — change from the previous period (balance)",
    "derived.unit_labour_cost_hour.PT.rebase_100":
        "Unit labour cost per hour — rebased index (2015 = 100)",
}

# --- base-series catalogue (project 4) -------------------------------------------------------
# The English edition is not shipped in v1: the tables exist so a render in `en` fails with
# MissingText (a clean refusal) instead of AttributeError. Populate with the PT review.
FAMILIES: dict[str, str] = {}
SELF_LOCATING_FAMILIES: frozenset[str] = frozenset()
GEOGRAPHIES: dict[str, str] = {}
BASE_UNITS: dict[str, str] = {}
FLAGS: dict[str, str] = {}
THEMES: dict[str, str] = {}
THEME_BLURBS: dict[str, str] = {}
FREQUENCIES: dict[str, str] = {}
SEASONAL: dict[str, str] = {}
SOURCE_TITLES: dict[str, str] = {}
WITHHELD_NOTES: dict[str, str] = {}
CURATED_HOME: list[dict] = []
SEARCH_ALIASES: dict[str, str] = {}
PAGES: dict[str, dict[str, str]] = {}  # v1 is PT-only; a missing slug raises MissingText
COMPARISONS_INTRO = ""
COMPARISONS: dict[str, dict[str, str]] = {}
