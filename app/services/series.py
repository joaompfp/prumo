from ..database import get_db, fetch_series
from ..constants import CATALOG, COMPARE_COUNTRIES

from stats_lib.sources.eurostat import EurostatSource
from stats_lib._country_labels import COUNTRY_LABELS

_eurostat = EurostatSource()

# EU27 member state codes (Eurostat convention: EL for Greece)
EU27_CODES = frozenset([
    'AT','BE','BG','CY','CZ','DE','DK','EE','EL','ES',
    'FI','FR','HR','HU','IE','IT','LT','LU','LV','MT',
    'NL','PL','PT','RO','SE','SI','SK',
])
EU_AGGREGATES = frozenset(['EU27','EU27_2020','EU'])

# In the DB, Eurostat monthly aggregate is stored under region 'EU27'.
# 'EU27_2020' only has sparse annual data from a different source.
# Map UI → DB for EUROSTAT region queries; reverse map is used to restore the UI key.
_EUROSTAT_REGION_DB = {'EU27_2020': 'EU27', 'EU': 'EU27'}
_EUROSTAT_REGION_DB_REV = {v: k for k, v in _EUROSTAT_REGION_DB.items()}


def _eu_db_regions(regions):
    """Translate UI region codes to DB region codes for EUROSTAT queries.
    Returns (db_regions, reverse_map) where reverse_map[db_key] = ui_key."""
    db_regions = [_EUROSTAT_REGION_DB.get(r, r) for r in regions]
    rev = {_EUROSTAT_REGION_DB[r]: r for r in regions if r in _EUROSTAT_REGION_DB}
    return db_regions, rev


# Composite indicators: blend high-quality Eurostat (EU27) with WorldBank (global)
COMPOSITE_INDICATORS = {
    "unemployment": {
        "eu":    ("EUROSTAT",  "unemployment"),
        "world": ("WORLDBANK", "unemployment_wb"),
    },
    "employment_rate": {
        "eu":    ("EUROSTAT",  "employment_rate"),
        "world": ("WORLDBANK", "employment_rate"),
    },
}


def query_composite(key: str, countries: str, since_yr: str = None) -> dict:
    """Blend Eurostat (EU27, high frequency) + WorldBank (global, annual) for a composite indicator.

    EU27 countries use Eurostat data; all other countries use WorldBank.
    EU aggregates (EU27_2020, EU) use Eurostat.
    """
    comp = COMPOSITE_INDICATORS[key]
    regions = [c.strip() for c in countries.split(",") if c.strip()]

    eu_regions    = [r for r in regions if r in EU27_CODES or r in EU_AGGREGATES]
    world_regions = [r for r in regions if r not in EU27_CODES and r not in EU_AGGREGATES]

    since_clause = f"AND period >= '{since_yr}'" if since_yr else ""
    series_map: dict[str, list] = {}

    conn = get_db()
    try:
        if eu_regions:
            eu_src, eu_ind = comp["eu"]
            db_eu_regions, eu_rev = _eu_db_regions(eu_regions)
            ph = ','.join(['?' for _ in db_eu_regions])
            rows = conn.execute(
                f"SELECT region, period, value FROM indicators "
                f"WHERE source=? AND indicator=? AND region IN ({ph}) {since_clause} "
                f"ORDER BY region, period",
                [eu_src, eu_ind] + db_eu_regions,
            ).fetchall()
            for db_region, period, value in rows:
                ui_region = eu_rev.get(db_region, db_region)
                series_map.setdefault(ui_region, []).append({"period": period, "value": value})

        if world_regions:
            w_src, w_ind = comp["world"]
            ph = ','.join(['?' for _ in world_regions])
            rows = conn.execute(
                f"SELECT region, period, value FROM indicators "
                f"WHERE source=? AND indicator=? AND region IN ({ph}) {since_clause} "
                f"ORDER BY region, period",
                [w_src, w_ind] + world_regions,
            ).fetchall()
            for region, period, value in rows:
                series_map.setdefault(region, []).append({"period": period, "value": value})
    finally:
        conn.close()

    series = [
        {"country": r, "label": COUNTRY_LABELS.get(r, r), "data": series_map[r]}
        for r in regions if r in series_map
    ]
    return {
        "dataset": f"composite:{key}",
        "source":  "COMPOSITE",
        "series":  series,
        "note":    None if series else "Dados não disponíveis.",
    }


def query_series(sources, indicators, from_p, to_p):
    """Query time series data for one or more source+indicator pairs.

    Args:
        sources: list of source names
        indicators: list of indicator names (same length as sources)
        from_p: start period filter (YYYY-MM) or None
        to_p: end period filter (YYYY-MM) or None

    Returns:
        list of dicts with source, indicator, label, unit, data
    """
    result = []
    for src, ind in zip(sources, indicators):
        src = src.strip()
        ind = ind.strip()
        meta = CATALOG.get(src, {}).get("indicators", {}).get(ind, {})
        data = fetch_series(src, ind, from_p, to_p)
        unit = meta.get("unit") or (data[0]["unit"] if data else "")
        result.append({
            "source":    src,
            "indicator": ind,
            "label":     meta.get("label", ind),
            "unit":      unit,
            "data":      [{"period": r["period"], "value": r["value"]} for r in data]
        })

    return result


def query_compare(dataset, countries, months, indicator=None, source="EUROSTAT", since_yr=None):
    """Query comparison data across countries.

    Args:
        dataset: dataset key (e.g. 'manufacturing')
        countries: comma-separated country codes string
        months: number of months to include
        indicator: direct DB indicator name (V5 mode) or None for legacy Eurostat
        source: source name for V5 mode (default EUROSTAT)
        since_yr: minimum period filter (e.g. '2020') or None

    Returns:
        dict with dataset, label, countries, months, series, note
    """
    regions = [c.strip() for c in countries.split(",")]

    # V5 mode: direct indicator query (bypasses Eurostat client)
    if indicator:
        conn = get_db()
        try:
            db_regions = regions
            region_rev = {}
            if source == "EUROSTAT":
                db_regions, region_rev = _eu_db_regions(regions)
            placeholders = ','.join(['?' for _ in db_regions])
            sql = f"""
                SELECT region, period, value FROM indicators
                WHERE source=? AND indicator=? AND region IN ({placeholders})
                {f"AND period >= '{since_yr}'" if since_yr else ''}
                ORDER BY region, period
            """
            rows = conn.execute(sql, [source, indicator] + db_regions).fetchall()
        finally:
            conn.close()

        # Group by region (map DB keys back to UI keys)
        series_map = {}
        for db_region, period, value in rows:
            ui_region = region_rev.get(db_region, db_region)
            series_map.setdefault(ui_region, []).append({"period": period, "value": value})

        series = [
            {
                "country": r,
                "label":   COUNTRY_LABELS.get(r, r),
                "data":    series_map.get(r, []),
            }
            for r in regions if r in series_map
        ]
        payload = {
            "dataset":   indicator,
            "label":     indicator,
            "source":    source,
            "countries": {r: COUNTRY_LABELS.get(r, r) for r in regions},
            "months":    months,
            "series":    series,
            "note":      None if series else "Dados não disponíveis.",
        }
        return payload

    # Legacy mode: Eurostat IPI datasets
    series  = _eurostat.get_series(dataset, regions, months)
    payload = {
        "dataset":   dataset,
        "label":     EurostatSource.DATASETS.get(dataset, {}).get("label", dataset),
        "countries": {r: COUNTRY_LABELS.get(r, r) for r in regions},
        "months":    months,
        "series":    series,
        "note":      None if series else "Dados não disponíveis.",
    }
    return payload
