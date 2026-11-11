### Task 3: Models and indicator registry

**Files:**
- Create: `ingest/models.py`, `ingest/registry.py`, `registry/core.yaml` (empty skeleton, filled in Task 8), `tests/ingest/test_models.py`, `tests/ingest/test_registry.py`

**Interfaces:**
- Produces: Pydantic models `Observation(series_id: str, period: str, value_text: str, value: float, status_flag: str | None, released_at: datetime | None)` and `SeriesSpec` (mirrors `series` + source info); `ingest.models.normalize_period(raw: str, frequency: str) -> str` (raises `ValueError`); `ingest.registry.load_registry(path: Path) -> list[SeriesSpec]`; `ingest.registry.sync_registry(db: Db, specs: list[SeriesSpec]) -> None` (upsert source+series).

- [ ] **Step 1: Write failing tests:** `test_normalize_period` table-driven: `("Setembro de 2025","M")→"2025-09"`, `("2025","A")→"2025"`, `("2025Q3","Q")→"2025-Q3"`, `("3º Trimestre de 2025","Q")→"2025-Q3"`, `("2025-S1","S")→"2025-S1"`, `("2025M09","M")→"2025-09"`; `test_normalize_period_rejects_garbage` (`"n/d"`, `""`, `"2025-13"`); `test_observation_rejects_non_numeric` (`":"`, `".."`, `""`); `test_registry_exactly_one_primary_per_indicator_key`; `test_registry_requires_licence_fields`; `test_sync_registry_idempotent`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (Portuguese month/quarter names in a lookup; registry validator raises on 0 or >1 primary per `indicator_key`). **Step 4: Run** → PASS. **Step 5: Commit.**

---

