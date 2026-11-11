### Task 4: Raw store

**Files:** Create `ingest/rawstore.py`, `tests/ingest/test_rawstore.py`

**Interfaces:**
- Produces: `RawStore(root: Path)` with `save(source: str, body: bytes) -> tuple[str, Path]` (returns `sha256`, path; idempotent; writes via temp file + atomic rename; gzip not applied to keep bytes verbatim) and `load(path: Path) -> bytes`.

- [ ] **Step 1: Failing tests:** `test_save_returns_sha256_and_path`; `test_save_is_idempotent` (second save doesn't rewrite, same path); `test_load_roundtrip_is_byte_identical`; `test_partial_write_never_visible` (monkeypatch rename to raise → no final file exists).
- [ ] **Step 2–4:** run (FAIL) → implement → run (PASS). **Step 5: Commit.**

---

