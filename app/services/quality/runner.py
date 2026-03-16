"""Main runner — orchestrates all quality checks."""

from datetime import datetime

from ...constants import CATALOG
from ...database import get_db
from .check_drift import _check_catalog_drift
from .check_orphan import _check_orphan_db
from .check_freshness import _check_freshness
from .check_flatline import _check_flatline
from .check_coverage import _check_region_coverage
from .check_spike import _check_spikes
from .check_gap import _check_gaps
from .check_cross_source import _check_cross_source


def run_quality_checks() -> dict:
    """Run all quality checks. Returns a structured JSON-serialisable report."""
    conn = get_db()

    pt_rows = conn.execute("""
        SELECT source, indicator,
               COUNT(*) as cnt,
               MIN(period) as since,
               MAX(period) as until,
               MAX(fetched_at) as last_fetch
        FROM indicators
        WHERE region = 'PT'
        GROUP BY source, indicator
    """).fetchall()

    all_rows = conn.execute("""
        SELECT source, indicator,
               COUNT(*) as cnt,
               COUNT(DISTINCT region) as n_regions,
               MIN(period) as since,
               MAX(period) as until
        FROM indicators
        GROUP BY source, indicator
    """).fetchall()

    db_stats_pt = {
        (r[0], r[1]): {"cnt": r[2], "since": r[3], "until": r[4], "last_fetch": r[5]}
        for r in pt_rows
    }
    db_stats_all = {
        (r[0], r[1]): {"cnt": r[2], "n_regions": r[3], "since": r[4], "until": r[5]}
        for r in all_rows
    }

    issues = (
        _check_catalog_drift(db_stats_pt, db_stats_all)
        + _check_orphan_db(db_stats_all)
        + _check_freshness(db_stats_pt)
        + _check_flatline(conn)
        + _check_region_coverage(conn)
        + _check_spikes(conn)
        + _check_gaps(conn)
        + _check_cross_source(conn)
    )

    # Group by check type, preserve order
    by_check: dict[str, list] = {}
    for issue in issues:
        by_check.setdefault(issue["check"], []).append(issue)

    severities = [i["severity"] for i in issues]
    catalog_keys = {
        (src, ind)
        for src, src_info in CATALOG.items()
        for ind in src_info.get("indicators", {})
    }
    # Only count catalog indicators (not orphan_db entries) as having issues
    catalog_with_issues = {
        (i["source"], i["indicator"]) for i in issues
        if (i["source"], i["indicator"]) in catalog_keys
    }
    total_catalog = len(catalog_keys)
    summary = {
        "errors":   severities.count("error"),
        "warnings": severities.count("warning"),
        "info":     severities.count("info"),
        "total":    len(issues),
        "ok":       total_catalog - len(catalog_with_issues),
    }

    return {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
        "checks":  by_check,
    }
