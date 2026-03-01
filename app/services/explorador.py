from ..database import get_db
from ..constants import CATALOG


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

    items = []
    for src, ind, regions, since, until, total in rows:
        cat_info = CATALOG.get(src, {}).get("indicators", {}).get(ind, {})
        items.append({
            "source":       src,
            "indicator":    ind,
            "label":        cat_info.get("label", ind),
            "category":     cat_info.get("tags", [src.lower()])[0] if cat_info.get("tags") else src.lower(),
            "tags":         cat_info.get("tags", []),
            "unit":         cat_info.get("unit", ""),
            "region_count": regions,
            "since":        since,
            "until":        until,
            "rows":         total,
        })
    return {"items": items, "total": len(items)}
