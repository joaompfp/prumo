import re
from ..database import get_db
from ..constants import CATALOG


def _infer_frequency(period: str) -> str:
    """Derive update frequency from period string format."""
    if not period:
        return ""
    if re.search(r'-Q\d', period):
        return "quarterly"
    if re.search(r'-W\d', period):
        return "weekly"
    if re.search(r'\sS\d', period):   # e.g. "2016 S1" — semestral
        return "semester"
    if re.match(r'^\d{4}-\d{2}$', period):
        return "monthly"
    if re.match(r'^\d{4}$', period):
        return "annual"
    return ""


def build_explorador_catalog():
    """Build /api/explorador — enhanced catalog with DB stats for filter panel."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT source, indicator, COUNT(DISTINCT region) as regions,
                   MIN(period) as since, MAX(period) as until, COUNT(*) as total_rows
            FROM indicators
            GROUP BY source, indicator
            ORDER BY source, indicator
        """).fetchall()
    finally:
        conn.close()

    # Duplicate FRED indicators (un-prefixed versions of commodity_* series)
    _FRED_DUPES = {"cotton", "iron_ore", "nickel", "soybean", "steel", "sugar", "zinc"}
    # Indicators with non-ASCII chars in name that break URL encoding
    _BROKEN_NAMES = {"natgas_price_domestic_€_per_GJ", "natgas_price_domestic_€_per_MWh",
                     "natgas_price_industry_€_per_GJ", "natgas_price_industry_€_per_MWh"}
    # Indicators with insufficient data to be useful in charts
    _SPARSE = {"industrial_eu_band_ia_excl_taxes",
               "industrial_eu_band_ib_excl_taxes", "industrial_eu_band_ic_excl_taxes"}

    items = []
    for src, ind, regions, since, until, total in rows:
        cat_info = CATALOG.get(src, {}).get("indicators", {}).get(ind, {})

        # Skip discontinued series and FRED duplicates
        if cat_info.get("discontinued"):
            continue
        if src == "FRED" and ind in _FRED_DUPES:
            continue
        if ind in _BROKEN_NAMES or ind in _SPARSE:
            continue

        freq = cat_info.get("frequency") or _infer_frequency(since or "")
        items.append({
            "source":       src,
            "indicator":    ind,
            "label":        cat_info.get("label", ind),
            "category":     cat_info.get("tags", [src.lower()])[0] if cat_info.get("tags") else src.lower(),
            "tags":         cat_info.get("tags", []),
            "unit":         cat_info.get("unit", ""),
            "frequency":    freq,
            "region_count": regions,
            "since":        since,
            "until":        until,
            "rows":         total,
        })
    return {"items": items, "total": len(items)}
