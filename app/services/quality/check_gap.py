"""Check 7: gap detection — missing months in monthly PT series."""

from datetime import date

from ...constants import CATALOG
from .period_utils import _ym_diff_months


def _check_gaps(conn) -> list:
    """Detect missing months in monthly PT series (gaps >1 month in last 24 months)."""
    issues = []
    today = date.today()
    cutoff_y = today.year - 2
    cutoff_ym = f"{cutoff_y}-{today.month:02d}"

    for src, src_info in CATALOG.items():
        for ind, meta in src_info.get("indicators", {}).items():
            if meta.get("frequency") != "monthly":
                continue
            try:
                rows = conn.execute(
                    "SELECT DISTINCT period FROM indicators "
                    "WHERE source=? AND indicator=? AND region='PT' AND period >= ? "
                    "AND length(period)=7 "
                    "ORDER BY period",
                    [src, ind, cutoff_ym]
                ).fetchall()
            except Exception:
                continue
            periods = [r[0] for r in rows]
            if len(periods) < 3:
                continue
            # Check for gaps between consecutive months
            gaps = []
            for i in range(1, len(periods)):
                diff = _ym_diff_months(periods[i], periods[i - 1])
                if diff > 1:
                    gaps.append(f"{periods[i-1]}→{periods[i]} ({diff}m)")
            if gaps and len(gaps) <= 3:
                issues.append({
                    "source": src, "indicator": ind,
                    "severity": "warning", "check": "gap",
                    "msg": f"gaps in last 24m: {', '.join(gaps)}",
                })
    return issues
