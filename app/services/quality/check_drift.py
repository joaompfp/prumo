"""Check 1: catalog_drift — DB rows/since/until vs catalog metadata."""

from ...constants import CATALOG
from .period_utils import _period_to_ym


def _check_catalog_drift(db_stats_pt: dict, db_stats_all: dict) -> list:
    """Compare catalog expected rows/since/until against DB reality."""
    issues = []

    for src, src_info in CATALOG.items():
        for ind, meta in src_info.get("indicators", {}).items():
            # Skip discontinued series
            if meta.get("discontinued"):
                continue

            key = (src, ind)
            # Prefer PT stats; fall back to total if indicator is PT-only source
            stats = db_stats_pt.get(key) or db_stats_all.get(key)

            if not stats:
                issues.append({
                    "source": src, "indicator": ind,
                    "severity": "error", "check": "catalog_drift",
                    "msg": "in catalog but NOT found in DB",
                })
                continue

            actual_cnt   = stats["cnt"]
            actual_until = stats["until"]
            exp_rows     = meta.get("rows")
            exp_until    = meta.get("until")

            # Row count check
            if exp_rows and actual_cnt:
                diff = actual_cnt - exp_rows
                if actual_cnt < exp_rows * 0.80:
                    issues.append({
                        "source": src, "indicator": ind,
                        "severity": "error", "check": "catalog_drift",
                        "msg": f"rows: expected {exp_rows}, actual {actual_cnt} (lost {exp_rows - actual_cnt} rows)",
                    })
                elif diff != 0:
                    issues.append({
                        "source": src, "indicator": ind,
                        "severity": "info", "check": "catalog_drift",
                        "msg": f"rows: expected {exp_rows}, actual {actual_cnt} ({'+'  if diff > 0 else ''}{diff} — update catalog)",
                    })

            # Until date: only warn when catalog says newer than DB (data regression)
            if exp_until and actual_until:
                exp_ym = _period_to_ym(exp_until)
                act_ym = _period_to_ym(actual_until)
                if exp_ym and act_ym and act_ym < exp_ym:
                    issues.append({
                        "source": src, "indicator": ind,
                        "severity": "warning", "check": "catalog_drift",
                        "msg": f"until: catalog says {exp_until}, DB only has {actual_until}",
                    })

    return issues
