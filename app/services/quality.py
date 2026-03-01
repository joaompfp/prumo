"""
quality.py — Data quality checks for CAE Dashboard.

Checks:
  catalog_drift    — DB rows/since/until vs catalog metadata
  orphan_db        — indicators in DB with no catalog entry (show raw code in Ficha)
  freshness        — are indicators being collected within expected window?
  flatline         — last 6 monthly values identical (stale pipeline?)
  region_coverage  — key regions present for comparativos indicators

Run via:  GET /api/quality
"""

from datetime import date, datetime
from ..database import get_db
from ..constants import CATALOG


# ── Period normalisation ──────────────────────────────────────────────────────

def _period_to_ym(period: str) -> str | None:
    """Normalise any period string to YYYY-MM for comparison."""
    if not period:
        return None
    p = period.strip()
    if len(p) == 4 and p.isdigit():          # "YYYY" → annual → Dec
        return f"{p}-12"
    if len(p) == 7 and p[4] == '-':
        suffix = p[5:]
        if suffix[0] == 'Q' and suffix[1:].isdigit():   # YYYY-Q1..Q4
            return f"{p[:4]}-{int(suffix[1:]) * 3:02d}"
        if suffix[0] == 'H' and suffix[1:].isdigit():   # YYYY-H1/H2
            return f"{p[:4]}-{int(suffix[1:]) * 6:02d}"
        return p                                         # YYYY-MM
    if len(p) == 9 and ' S' in p:            # "YYYY S1" / "YYYY S2"
        year, _, sem = p.partition(' S')
        return f"{year}-{int(sem) * 6:02d}"
    return p


def _ym_diff_months(a_ym: str, b_ym: str) -> int:
    """Return a - b in months (positive → a is newer). Both must be YYYY-MM."""
    try:
        ay, am = int(a_ym[:4]), int(a_ym[5:7])
        by_, bm = int(b_ym[:4]), int(b_ym[5:7])
        return (ay - by_) * 12 + (am - bm)
    except Exception:
        return 0


# ── Check 1: catalog_drift ────────────────────────────────────────────────────

def _check_catalog_drift(db_stats_pt: dict, db_stats_all: dict) -> list:
    """Compare catalog expected rows/since/until against DB reality."""
    issues = []

    for src, src_info in CATALOG.items():
        for ind, meta in src_info.get("indicators", {}).items():
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


# ── Check 2: orphan_db ────────────────────────────────────────────────────────

# Legacy Eurostat dataset codes that are intentionally un-cataloged
_LEGACY_PREFIXES = ("STS_INPR_M_",)
# Sources that are entirely multi-region and don't need catalog entries per-indicator
_SKIP_ORPHAN_SOURCES: set[str] = set()


def _check_orphan_db(db_stats_all: dict) -> list:
    """Find indicators in DB that have no catalog entry — they show raw codes in Ficha."""
    catalog_keys = {
        (src, ind)
        for src, src_info in CATALOG.items()
        for ind in src_info.get("indicators", {})
    }
    issues = []
    for (src, ind), stats in sorted(db_stats_all.items()):
        if (src, ind) in catalog_keys:
            continue
        if src in _SKIP_ORPHAN_SOURCES:
            continue
        if any(ind.startswith(p) for p in _LEGACY_PREFIXES):
            continue
        issues.append({
            "source": src, "indicator": ind,
            "severity": "warning", "check": "orphan_db",
            "msg": (
                f"{stats['cnt']} rows, {stats['n_regions']} region(s), "
                f"{stats['since']}–{stats['until']} — no catalog entry, shows raw code in Ficha"
            ),
        })
    return issues


# ── Check 3: freshness ────────────────────────────────────────────────────────

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


# ── Check 4: flatline ─────────────────────────────────────────────────────────

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


# ── Check 5: region_coverage ──────────────────────────────────────────────────

_KEY_REGIONS = {
    "EUROSTAT":  ["PT", "DE", "FR", "ES", "EU27"],
    "WORLDBANK": ["PT", "US", "BR", "DE"],
}

# EU27 and EU27_2020 are different Eurostat codes for the same aggregate
_EU27_EQUIV = frozenset(["EU27", "EU27_2020"])


def _region_present(region: str, available: set) -> bool:
    """Check presence, treating EU27 and EU27_2020 as equivalent."""
    if region in available:
        return True
    if region in _EU27_EQUIV:
        return bool(available & _EU27_EQUIV)
    return False


def _check_region_coverage(conn) -> list:
    """For comparativos indicators, verify key regions are present in DB."""
    from ..constants.compare_catalog import COMPARATIVOS_CATALOG

    issues = []
    region_cache: dict[tuple, set] = {}

    for entry in COMPARATIVOS_CATALOG:
        src = entry.get("source")
        ind = entry.get("indicator")
        if not src or not ind or entry.get("mode") == "legacy":
            continue
        if src not in _KEY_REGIONS:
            continue

        key = (src, ind)
        if key not in region_cache:
            try:
                rows = conn.execute(
                    "SELECT DISTINCT region FROM indicators WHERE source=? AND indicator=?",
                    [src, ind]
                ).fetchall()
                region_cache[key] = {r[0] for r in rows}
            except Exception:
                region_cache[key] = set()

        available = region_cache[key]
        missing = [r for r in _KEY_REGIONS[src] if not _region_present(r, available)]
        if missing:
            issues.append({
                "source": src, "indicator": ind,
                "severity": "warning", "check": "region_coverage",
                "msg": f"missing key regions: {', '.join(missing)}",
            })

    return issues


# ── Main runner ───────────────────────────────────────────────────────────────

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
