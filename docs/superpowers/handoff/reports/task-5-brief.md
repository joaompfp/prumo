### Task 5: Validators and quarantine

**Files:** Create `ingest/validate.py`, `tests/ingest/test_validate.py`

**Interfaces:**
- Consumes: `Observation`, `SeriesSpec`.
- Produces: `validate(spec: SeriesSpec, rows: Iterable[RawRow]) -> tuple[list[Observation], list[Rejection]]` where `RawRow(period_raw: str, value_raw: str, unit_raw: str | None, flag_raw: str | None)` and `Rejection(period_raw, value_raw, reason)`. Rules: period normalizes for `spec.frequency`; value numeric (accepts comma decimal, exact string preserved); unit (if provided) equals `spec.unit` else reject; duplicate periods within a payload rejected (both); reasons are fixed strings: `bad_period`, `non_numeric`, `unit_mismatch`, `duplicate_period`.

- [ ] **Step 1: Failing tests:** one per reason; `test_comma_decimal_preserves_text` (`"1 234,5"` → `value_text == "1 234,5"`, `value == 1234.5`); `test_no_rounding` (`"0.30000000000000004"` stays); `test_dash_and_colon_are_non_numeric`.
- [ ] **Step 2–4:** FAIL → implement → PASS. **Step 5: Commit.**

---

