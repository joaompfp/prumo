# Task 9 report — Eurostat adapter + independent verifier (running log)

## Done
- [x] `ingest/flags.py` + `tests/ingest/test_flags.py` (RED: ModuleNotFoundError at collection; GREEN: 45 passed)
- [x] registry mapping (native_code/url) + unmapped-eurostat.md (598 active / 99 inactive) — commit f467b5d
- [x] `ingest/sources/eurostat.py` + fixtures + tests (RED: collection error with module moved aside; GREEN: 36 passed); flag 'i' (imputed) added -> estimated
- [ ] `ingest/verifiers/eurostat.py` + tests
- [ ] live test
