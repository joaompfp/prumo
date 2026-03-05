# CAE Dashboard — Data Normalization Architecture

> **Status:** WP-E3 script ready; WP-E4 architecture proposed (pending Analyst unit audit before implementation).
> Last updated: 2026-03-02

---

## 1. Current State

### Database: `cae-data.duckdb`

Schema version: `1` (stored in `meta` table)

#### Table: `indicators`

| Column      | Type    | Notes                                      |
|-------------|---------|---------------------------------------------|
| source      | VARCHAR | BPORTUGAL, DGEG, ERSE, EUROSTAT, FRED, INE, OECD, REN, WORLDBANK |
| indicator   | VARCHAR | Snake-case indicator name                  |
| region      | VARCHAR | Usually `PT` or country ISO code           |
| period      | VARCHAR | See period formats below                   |
| value       | DOUBLE  | Numeric value (may be NULL)                |
| unit        | VARCHAR | Unit string (not standardised across sources) |
| category    | VARCHAR | Thematic group (fuel_prices, gdp, etc.)    |
| detail      | VARCHAR | JSON string with metadata (e.g. period_type) |
| fetched_at  | VARCHAR | ISO8601 timestamp of last fetch            |
| source_id   | VARCHAR | Source file or API reference               |

**Row count:** ~184,784 rows  
**No explicit indexes** — DuckDB uses columnar scan (efficient for OLAP workloads)

#### Row distribution by source

| Source      | Rows    |
|-------------|---------|
| EUROSTAT    | 122,495 |
| WORLDBANK   | 31,667  |
| INE         | 9,534   |
| DGEG        | 7,223   |
| FRED        | 5,647   |
| BPORTUGAL   | 3,441   |
| REN         | 2,688   |
| OECD        | 1,572   |
| ERSE        | 517     |

#### Period formats in use

| Format      | Example       | Sources                         | Count  |
|-------------|---------------|---------------------------------|--------|
| `YYYY`      | `2024`        | EUROSTAT, WORLDBANK, DGEG, ERSE | 42,588 |
| `YYYY-MM`   | `2024-03`     | All sources                     | 142,196|
| `YYYY SN`   | `2016 S1`     | DGEG (industrial electricity bands) | ~207 |

**No quarterly (`YYYY-QN`) periods exist in the current DB.**  
The `normalisePeriod()` JS function handles quarterly for future compatibility.

---

## 2. Period Normalisation (WP-E5 — Frontend)

**Problem:** When comparing an annual series (`"2024"`) with a monthly series (`"2024-03"`),
the periods are treated as distinct strings on the X-axis. `"2024"` never aligns with any
month.

**Fix (implemented in `static/js/sections/analise.js`):**

```javascript
function normalisePeriod(p) {
  if (!p) return p;
  if (/^\d{4}$/.test(p)) return `${p}-12`;              // Annual → December
  const qm = p.match(/^(\d{4})[- ]Q(\d)$/);
  if (qm) return `${qm[1]}-${String(parseInt(qm[2]) * 3).padStart(2, '0')}`;  // Quarterly
  const sm = p.match(/^(\d{4})[- ][SH](\d)$/);
  if (sm) return `${sm[1]}-${sm[2] === '1' ? '06' : '12'}`;  // Semi-annual
  return p;  // Monthly — as-is
}
```

**Normalisation mapping:**

| Raw period  | Normalised | Rationale                               |
|-------------|------------|-----------------------------------------|
| `"2024"`    | `"2024-12"` | Annual value pinned to December        |
| `"2025-Q3"` | `"2025-09"` | End of Q3 = September                  |
| `"2016 S1"` | `"2016-06"` | End of H1 = June                       |
| `"2016 S2"` | `"2016-12"` | End of H2 = December                   |
| `"2024-03"` | `"2024-03"` | Monthly — unchanged                    |

**Display:** `fmt.period(p, { annualCollapsed: true })` in `static/js/api.js` renders
`"2024-12"` as `"2024"` (not `"Dez 24"`) when it originated from an annual period.

---

## 3. Value Normalisation (WP-E3 — Script)

**Script:** `scripts/normalize_db.py`

Applies unit-conversion rules from the `RULES` list to the `indicators` table.

### Current rules

| Source | Indicator | Operation | Factor | Old unit | New unit | Status |
|--------|-----------|-----------|--------|----------|----------|--------|
| DGEG   | aviation_jet_fuel | ÷1000 | 1000 | EUR/m³ | EUR/l | **ALREADY_DONE** (in DB) |

### Usage

```bash
# Dry-run (safe — no DB changes):
python3 scripts/normalize_db.py

# Apply to DB:
python3 scripts/normalize_db.py --apply

# Apply for specific source only:
python3 scripts/normalize_db.py --source DGEG --apply

# Custom DB path:
python3 scripts/normalize_db.py --db /data/cae-data.duckdb --apply
```

> **After Analyst unit audit:** add new rules to the `RULES` list in the script
> with format `(source, indicator, operation, factor, old_unit, new_unit, reason)`.

---

## 4. Proposed Architecture: raw / normalized separation (WP-E4)

> **NOT YET IMPLEMENTED.** Awaiting Analyst unit audit sign-off.

### Problem with current single-table design

- Running `normalize_db.py --apply` mutates values in-place — **not idempotent** if
  compound-run accidentally.
- No way to distinguish "raw from API" from "normalised by pipeline" without auditing code.

### Proposed schema

```sql
-- Raw values — never mutated after fetch
CREATE TABLE indicators_raw AS SELECT * FROM indicators;
-- Implicit PK: (source, indicator, region, period)
-- Suggested indexes:
CREATE INDEX idx_raw_source_indicator ON indicators_raw (source, indicator);
CREATE INDEX idx_raw_period ON indicators_raw (period);

-- Canonical normalised table (current indicators, repurposed)
ALTER TABLE indicators ADD COLUMN norm_applied BOOLEAN DEFAULT FALSE;
ALTER TABLE indicators ADD COLUMN norm_version INTEGER;

-- Convenience view (always returns canonical values)
CREATE VIEW indicators_v AS
  SELECT
    n.source, n.indicator, n.region, n.period,
    COALESCE(n.value, r.value) AS value,
    COALESCE(n.unit, r.unit)   AS unit,
    n.category, n.detail, n.fetched_at, n.source_id,
    n.norm_applied, n.norm_version
  FROM indicators n
  JOIN indicators_raw r USING (source, indicator, region, period);
```

### Migration steps (pending Analyst sign-off)

1. `RENAME TABLE indicators TO indicators_raw`
2. `CREATE TABLE indicators AS SELECT *, FALSE AS norm_applied, NULL::INTEGER AS norm_version FROM indicators_raw`
3. `python3 scripts/normalize_db.py --apply` — applies RULES from raw

### Benefits

- `normalize_db.py --apply` is fully **idempotent**: always re-derives from `indicators_raw`
- Raw data is preserved for audit and re-processing
- `norm_applied` and `norm_version` allow tracking which rows were touched and when
- No risk of compounding conversion factors on repeated runs

---

## 5. Files changed / created

| File | WP | Change |
|------|----|--------|
| `static/js/sections/analise.js` | E5 | Added `normalisePeriod()`, `isAnnualPeriod()`, updated `renderChart()` and `renderTable()` |
| `static/js/api.js` | E5 | Updated `fmt.period(p, opts)` to accept `opts.annualCollapsed` |
| `scripts/normalize_db.py` | E3 | New script with RULES list and dry-run/apply modes |
| `docs/NORMALIZATION.md` | E4 | This file |
