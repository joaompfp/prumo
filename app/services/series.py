from ..database import get_db, fetch_series
from ..constants import CATALOG, COMPARE_COUNTRIES

from stats_lib.sources.eurostat import EurostatSource
from stats_lib._country_labels import COUNTRY_LABELS

_eurostat = EurostatSource()


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
            placeholders = ','.join(['?' for _ in regions])
            sql = f"""
                SELECT region, period, value FROM indicators
                WHERE source=? AND indicator=? AND region IN ({placeholders})
                {f"AND period >= '{since_yr}'" if since_yr else ''}
                ORDER BY region, period
            """
            rows = conn.execute(sql, [source, indicator] + regions).fetchall()
        finally:
            conn.close()

        # Group by region
        series_map = {}
        for region, period, value in rows:
            series_map.setdefault(region, []).append({"period": period, "value": value})

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
