"""Check 3: freshness — are indicators being collected within expected window?"""

from datetime import date

from ...constants import CATALOG
from .period_utils import _period_to_ym, _ym_diff_months

_DEFAULT_LAG = {"monthly": 2, "quarterly": 4, "semester": 7, "annual": 14}


def _check_freshness(db_stats_pt: dict) -> list:
    """Flag indicators whose last DB period is older than expected given frequency + lag."""
    issues = []
    today = date.today()
    today_ym = today.strftime("%Y-%m")

    for src, src_info in CATALOG.items():
        for ind, meta in src_info.get("indicators", {}).items():
            stats = db_stats_pt.get((src, ind))
            if not stats or not stats.get("until"):
                continue

            # Skip discontinued series
            if meta.get("discontinued"):
                continue

            freq     = meta.get("frequency", "monthly")
            lag      = meta.get("lag_months", _DEFAULT_LAG.get(freq, 3))
            grace    = 2   # extra months of tolerance
            total_lag = max(lag + grace, 2)   # minimum 2 months even for lag_months=0

            # Compute expected minimum "until" = today minus total lag
            exp_month = today.month - total_lag
            exp_year  = today.year
            while exp_month <= 0:
                exp_month += 12
                exp_year  -= 1
            expected_min_ym = f"{exp_year}-{exp_month:02d}"

            actual_ym = _period_to_ym(stats["until"])
            if not actual_ym:
                continue

            delta = _ym_diff_months(expected_min_ym, actual_ym)   # positive → actual is stale
            if delta > 0:
                sev = "error" if delta >= 6 else "warning"
                issues.append({
                    "source": src, "indicator": ind,
                    "severity": sev, "check": "freshness",
                    "msg": (
                        f"last period {stats['until']}, {delta}m behind "
                        f"expected minimum {expected_min_ym} (freq={freq}, lag={lag}m)"
                    ),
                })
    return issues
