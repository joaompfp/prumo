### Task 8: Legacy import and registry proposal

**Files:** Create `ingest/legacy_import.py`, `ingest/propose_registry.py`, `tests/ingest/test_legacy_import.py`, `tests/ingest/fixtures/legacy_sample.duckdb` (≤200 rows built by a helper in the test)

**Interfaces:**
- Produces: `legacy_import.import_legacy(db: Db, duckdb_path: Path) -> LegacyImportReport(n_imported, n_quarantined_by_reason: dict[str,int])` — reads the old `indicators` table (the only place `duckdb` is imported; add `duckdb` as a dev/migration-only dependency), writes `observation(kind='legacy-unverified', raw_fetch_id=NULL)` under a synthetic run in state `verified` but not served (`legacy_served` setting stays 0); null value/unit and unparseable periods → `quarantine`. `propose_registry.propose(duckdb_path: Path, out: Path) -> None` writes `registry/core.proposed.yaml`: one entry per (source, indicator, region) in the core themes with proposed `role`, `theme`, `frequency`, `unit`, source licence stubs, and an overlap report `registry/overlaps.md` listing indicators published by more than one source with the proposed primary (Portuguese institution first, else closest to origin).

- [ ] **Step 1: Failing tests:** `test_null_value_and_unit_quarantined`; `test_ine_free_text_period_normalized_or_quarantined`; `test_legacy_rows_not_in_served_view`; `test_import_is_idempotent`; `test_proposal_has_one_primary_per_indicator_key`; `test_proposal_prefers_portuguese_institution`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5:** run against the real `/data/cae-data.duckdb` on f0nix; save `registry/overlaps.md` and `core.proposed.yaml`; **stop and give the owner both files to review once** (spec §11.3). After review, copy to `registry/core.yaml`. **Step 6: Commit.**

---

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

