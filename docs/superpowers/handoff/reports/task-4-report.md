# Task 4 report: Raw store
Status: DONE. Commit 257793b.
Files: ingest/rawstore.py, tests/ingest/test_rawstore.py
RED: `pytest tests/ingest/test_rawstore.py` -> ModuleNotFoundError: No module named 'ingest.rawstore' (collection error).
GREEN: `pytest tests/ingest -q` -> 103 passed (rawstore: 12 cases incl. parametrized traversal).
Tests: the brief's four, test_save_rejects_path_traversal_source, test_load_detects_tampering, plus test_load_refuses_path_outside_root (the ValueError requirement for load).
Notes: temp file is created in the target directory (.tmp-*), fsynced, os.replace'd; temp is removed on failure. Existing-file fast path returns without rewrite. load resolves symlinks before the root check. No sqlite3/db imports.
Concerns: none. Existing-file check trusts presence (does not re-hash on save); load verifies.

## Fix round 1 (I-1)
Change: `save` now returns early only if the existing file's bytes equal `body` (same inode/mtime preserved); otherwise it rewrites via the same temp + fsync + os.replace path, repairing corrupt or zero-length files.
Tests: added `test_save_repairs_corrupt_existing_file` parametrized [corrupt (b"bad"), zero_length (b"")]; each asserts content restored, load succeeds, no stray temp files. test_save_is_idempotent unchanged and passing.
Command: `.venv-ci/bin/python -m pytest tests/ingest -v` -> `105 passed in 3.34s` (all 14 test_rawstore items PASSED, incl. the two repair cases and test_save_is_idempotent).
