"""Check 4: flatline — last 6 monthly values identical (stale pipeline?)."""

from ...constants import CATALOG


def _check_flatline(conn) -> list:
    """Detect monthly series where last 6 values are all identical."""
    issues = []
    for src, src_info in CATALOG.items():
        for ind, meta in src_info.get("indicators", {}).items():
            if meta.get("frequency") != "monthly":
                continue
            try:
                rows = conn.execute(
                    "SELECT value FROM indicators "
                    "WHERE source=? AND indicator=? AND region='PT' "
                    "ORDER BY period DESC LIMIT 6",
                    [src, ind]
                ).fetchall()
            except Exception:
                continue
            vals = [r[0] for r in rows if r[0] is not None]
            if len(vals) < 6:
                continue
            if len(set(vals)) == 1:
                issues.append({
                    "source": src, "indicator": ind,
                    "severity": "warning", "check": "flatline",
                    "msg": f"last 6 values all {vals[0]} — possible stale pipeline",
                })
    return issues
