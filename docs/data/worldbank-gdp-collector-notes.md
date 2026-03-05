# WorldBank GDP per capita PPP — Collector Notes

**Date:** 2026-02-28  
**Purpose:** Document WorldBank collector for implementing `gdp_per_capita_ppp` indicator  
**Author:** Scout (sub-agent)

---

## 1. WorldBank Collector Location

**File:** `collectors/worldbank.py`

**Structure:**
- Python class `WorldBankClient` with API wrapper for World Bank Indicators API v2
- No authentication required
- Base URL: `https://api.worldbank.org/v2`

---

## 2. Current Indicator Mapping

The collector defines indicators in the `INDICATORS` dict (lines 17-33):

```python
INDICATORS = {
    # Macro
    "gdp": "NY.GDP.MKTP.CD",              # GDP (current US$)
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",     # GDP growth (annual %)
    "gdp_per_capita": "NY.GDP.PCAP.CD",    # GDP per capita ⚠️ CURRENT USD, NOT PPP
    "inflation": "FP.CPI.TOTL.ZG",         # Inflation, consumer prices (annual %)
    "unemployment": "SL.UEM.TOTL.ZS",      # Unemployment, total (% of labor force)
    
    # ... (more indicators)
}
```

**Current DB status:**
- `gdp_per_capita` (NY.GDP.PCAP.CD) is already collected ✅
- Data: 2000-2024, all EU countries
- **Problem:** This is nominal USD per capita, NOT PPP-adjusted

---

## 3. Target Indicator for CAE Dashboard

**Series code:** `NY.GDP.PCAP.PP.CD`  
**Full name:** GDP per capita, PPP (constant 2017 international $)  
**Why PPP:** Adjusts for cost of living differences, enables proper cross-country comparison

**API Test Results (2026-02-28):**

```bash
curl -s "https://api.worldbank.org/v2/country/PT/indicator/NY.GDP.PCAP.PP.CD?format=json&per_page=10"
```

| Country | 2024 | 2023 | 2022 | Data Range |
|---------|------|------|------|------------|
| PT | 51,679.89 | 49,352.84 | 45,250.01 | 2020-2024 ✅ |
| ES | 57,965.29 | 55,682.24 | 51,398.93 | 2020-2024 ✅ |
| DE | 73,551.93 | 71,684.03 | 69,048.99 | 2020-2024 ✅ |
| EU | 63,585.41 | 61,368.11 | 58,483.71 | 2020-2024 ✅ |
| FR | 62,556.92 | 60,838.94 | 57,042.94 | 2020-2024 ✅ |

**Status:** All 5 target countries have fresh data (last 5 years).

---

## 4. How to Add the Indicator

### Step 1: Update `collectors/worldbank.py`

Add to the `INDICATORS` dict:

```python
INDICATORS = {
    # Macro
    "gdp": "NY.GDP.MKTP.CD",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "gdp_per_capita": "NY.GDP.PCAP.CD",        # Keep existing (nominal)
    "gdp_per_capita_ppp": "NY.GDP.PCAP.PP.CD", # ← ADD THIS LINE
    "inflation": "FP.CPI.TOTL.ZG",
    # ... rest unchanged
}
```

### Step 2: Run the collector

The collector is invoked via the `cae-collect` CLI:

```bash
cd /home/node/.openclaw/workspace/jarbas-stack/images/cae-dashboard

# Test fetch for Portugal
uv run --with requests python3 scripts/cae-collect worldbank get_indicator PT gdp_per_capita_ppp --start-year=2020

# Fetch for all EU countries
for country in PT ES DE FR EU; do
  uv run --with requests python3 scripts/cae-collect worldbank get_indicator $country gdp_per_capita_ppp --start-year=2000
done
```

**Note:** The `cae-collect` script expects methods on the client class. The `WorldBankClient.get_indicator(country, indicator, ...)` method accepts:
- `country`: ISO code (PT, ES, DE, EU, FR)
- `indicator`: Key from `INDICATORS` dict OR raw WorldBank code
- `start_year` / `end_year`: Optional period filter

### Step 3: Insert into DuckDB

The collector script should output JSON. To insert into the DB:

```python
import duckdb
import json

# Parse collector output
data = [
    {"source": "WORLDBANK", "indicator": "gdp_per_capita_ppp", "region": "PT", 
     "period": "2024", "value": 51679.89, "unit": "2017 intl $"},
    # ... more rows
]

conn = duckdb.connect('data/cae-data.duckdb')
conn.executemany(
    "INSERT INTO indicators (source, indicator, region, period, value, unit) VALUES (?, ?, ?, ?, ?, ?)",
    [(d['source'], d['indicator'], d['region'], d['period'], d['value'], d['unit']) for d in data]
)
conn.close()
```

**Alternative:** Check if `scripts/cae-v4-backfill.py` has a WorldBank backfill routine that can be extended.

### Step 4: Update API endpoint

**File:** `app/services/macro.py`

Add to the `build_macro()` function (around line 45):

```python
# GDP per capita PPP (new)
for country in ["PT", "ES", "DE", "EU", "FR"]:
    rows = fetch_series("WORLDBANK", "gdp_per_capita_ppp", region=country)
    if rows:
        result[f"gdp_per_capita_ppp_{country.lower()}"] = [
            {"period": r["period"], "value": r["value"]} for r in rows
        ]
```

### Step 5: Update catalog metadata

**File:** `app/constants/catalog.py`

Add to `CATALOG["WORLDBANK"]["indicators"]`:

```python
"gdp_per_capita_ppp": {
    "label": "PIB per capita (PPC)",
    "description": "Produto Interno Bruto per capita em paridades de poder de compra (PPC), USD constantes 2017. Ajustado para diferenças de custo de vida entre países, permitindo comparação directa de riqueza real.",
    "unit": "USD PPC 2017",
    "frequency": "annual",
    "source_url": "https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.CD",
},
```

---

## 5. Database Schema

**Table:** `indicators`

```sql
CREATE TABLE indicators (
    source TEXT,        -- 'WORLDBANK'
    indicator TEXT,     -- 'gdp_per_capita_ppp'
    region TEXT,        -- 'PT', 'ES', 'DE', 'EU', 'FR'
    period TEXT,        -- 'YYYY' (annual data)
    value DOUBLE,       -- 51679.89
    unit TEXT,          -- '2017 intl $' or 'USD PPC 2017'
    detail TEXT         -- Optional JSON metadata
);
```

**Existing WorldBank data in DB:**
```
gdp_per_capita (NY.GDP.PCAP.CD):   25 records per country (2000-2024)
rnd_pct_gdp:                        23 records per country (2000-2022)
fdi_inflows_pct_gdp:                25 records per country (2000-2024)
gdp_growth:                         25 records per country (2000-2024)
```

**After implementation:**
```
gdp_per_capita_ppp (NY.GDP.PCAP.PP.CD): 25 records per country (2000-2024) ← NEW
```

---

## 6. Key Differences: GDP per capita vs GDP per capita PPP

| Indicator | Code | Unit | Use Case |
|-----------|------|------|----------|
| **GDP per capita** (existing) | `NY.GDP.PCAP.CD` | Current USD | Nominal wealth in dollars (affected by exchange rates) |
| **GDP per capita PPP** (target) | `NY.GDP.PCAP.PP.CD` | 2017 intl $ (PPP) | Real purchasing power, comparable across countries |

**Example (2024 data):**
- PT nominal GDP/cap: ~$28,000 USD
- PT PPP GDP/cap: ~$51,680 (adjusted for cost of living)

PPP is the correct metric for cross-country wealth comparison on the CAE Dashboard.

---

## 7. Summary for Coder

**Task checklist:**

1. ✅ Verify API access (done by Scout — all 5 countries have 2020-2024 data)
2. ⬜ Edit `collectors/worldbank.py` → add `"gdp_per_capita_ppp": "NY.GDP.PCAP.PP.CD"` to INDICATORS dict
3. ⬜ Run collector for PT, ES, DE, EU, FR (years 2000-2024)
4. ⬜ Insert data into `indicators` table in DuckDB
5. ⬜ Update `app/services/macro.py` → add fetch logic
6. ⬜ Update `app/constants/catalog.py` → add metadata
7. ⬜ Test API endpoint `/api/macro` → verify `gdp_per_capita_ppp_pt` etc. are returned

**No edits needed to:**
- Database schema (existing `indicators` table is sufficient)
- API authentication (WorldBank API is public, no key needed)

**Critical notes:**
- Do NOT replace existing `gdp_per_capita` (NY.GDP.PCAP.CD) — keep both
- Use PPP version for dashboard charts (cross-country comparison)
- Unit: "2017 intl $" or "USD PPC 2017" (be consistent with existing WB indicators)

---

**EOF**
