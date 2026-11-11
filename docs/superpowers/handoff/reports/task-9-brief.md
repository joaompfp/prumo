# Task 9 brief (Eurostat adapter + independent verifier)

Extracted from the plan's combined 'Tasks 9–16' section; Task 9 = the Eurostat row of the table.

### Tasks 9–16: One source each (adapter + independent verifier)

Each task is the same shape and delivers `ingest/sources/<name>.py` (implements `Source`) and `ingest/verifiers/<name>.py` (implements `Verifier` through a **different endpoint or format** than the collector: e.g. API vs the publisher's downloadable file/CSV), plus `tests/ingest/test_source_<name>.py` and recorded fixtures in `tests/ingest/fixtures/<name>/` (real payloads fetched once, committed, ≤200 KB each).

| Task | Source | Collector reuse | Independent channel (builder confirms) | Scope |
|---|---|---|---|---|
| 9 | Eurostat | `collectors/eurostat.py` | bulk TSV download vs JSON-stat API | EU+PT economy, demography, energy |
| 10 | INE | `collectors/ine.py` | INE indicator page export vs API | PT economy, demography |
| 11 | Banco de Portugal | `collectors/bportugal.py` | BPstat bulk/CSV vs API | PT economy |
| 12 | REN (+ DGEG, ERSE if registry marks them core) | `collectors/ren.py`, `dgeg_fuel_api.py` | publisher CSV/portal vs API | PT energy |
| 13 | World Bank | `collectors/worldbank.py` | bulk CSV vs API v2 | world basics |
| 14 | FRED | `collectors/fred.py` | `fredgraph.csv` vs API | US/world reference series in registry |
| 15 | OECD | `collectors/oecd.py` | SDMX-CSV vs SDMX-JSON | registry-listed series |
| 16 | E-REDES/dadosgov | only if the registry marks series core | portal export vs API | registry-listed |

**Per-task steps (identical):**
- [ ] **Step 1: Failing tests:** `test_parse_fixture_yields_expected_rows` (assert exact `period`, `value_text`, `unit`, `status_flag` for ≥5 named observations copied from the fixture and cross-checked by hand against the publisher site); `test_parse_html_error_page_raises`; `test_parse_preserves_status_flags` (provisional/estimated mapped to the flag vocabulary in `ingest/flags.py`: `provisional`, `estimated`, `revised`, `break`, `normal`); `test_verifier_does_not_import_parser`; `test_verifier_detects_tampered_value` (change one `expected_text` → mismatch).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** the adapter (reuse the request logic from the existing collector but return `RawResponse`s; no DB access, no writes) and the verifier. If **no independent channel exists** for the source, do not invent one: record it in `registry/unverifiable.md`, mark the source `not served`, and report to the owner (spec §6b).
- [ ] **Step 4: Run** → PASS. **Step 5: Live smoke** on f0nix: `python -m ingest run <name> --dry-run` then `python -m ingest run <name>`; expect state `verified` and non-empty `served_observation` for that source. **Step 6: Commit.**

---
