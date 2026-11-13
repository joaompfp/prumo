# Task 11 independent review and controller verification

Scope: e382ecd..8c31802 initial implementation; 8c31802..550ad90 fix round 1. Branch pipeline-rebuild. No production deployment or main merge.

## Review gates

Independent specification review: PASS. Confirmed publisher-token preservation, dimension/stride identity, ten registry series, real fixtures, genuinely independent portal channel, licence attribution evidence, fail-closed status handling and required source/verifier/independence tests. Targeted suite 163 passed; reviewer also reran the original ingestion suite (735 passed, 3 live deselected).

Independent quality review: APPROVED with non-blocking findings. Concrete probes exercised dimension permutations, sparse/dense equivalence, flags, currency/geography drift and vintage selection. The sparse parser accepted aliased indices; the initial report overstated sparse test coverage. Deferred diagnostic minors: mixed naive/aware publication timestamps raise TypeError (still fail closed); missing pin category uses an unhelpful raw list.index error.

Controller follow-up identified incomplete unit audit evidence: only observations were archived, while units were extracted from a second metadata response. Ruling AC requires every response used in the decision to be preserved.

Fix round 1: cc094b9 rejects noncanonical sparse indices; 4d7107e bundles both exact portal responses in versioned evidence; 550ad90 updates the implementation report. Independent scoped re-review: specification PASS, quality APPROVED, 70 targeted tests passed, no Critical or Important findings remain. Offline envelope recovery and request-cache semantics independently exercised. No shared allowlist or dependency change.

## Final controller execution

`.venv-ci/bin/python -m pytest tests -q`
751 passed, 3 live deselected, 1 warning, 115.75 s.

`.venv-ci/bin/python -m pytest tests/ingest/test_live_bportugal.py -m live -s --basetemp=/home/joao/.hermes/cache/scratch/prumo-bportugal-live-final`
1 passed, 40.92 s. Run state verified, all ten active series present, 4,318 written and served in isolated SQLite, 78 non_numeric quarantines (German yield pre-2000 missing cells), sample 24/24 matched.

Controller independently opened the live SQLite and decoded all 24 archived evidence bundles: schema bportugal-portal-evidence, metadata and observations raw bodies present and recoverable offline. Source/verifier and touched tests pass Ruff 0.17.4. git diff --check clean.

Controller f0nix read-only HTTP probes: documented /data/v1/series and independent /api/observations both returned HTTP 200 with X-Throttle 1000. No service or infrastructure changes.

## Continuation boundary

Task 11 is complete through 550ad90. Task 12 (REN plus DGEG/ERSE where core) is next. Public app remains maintenance-only; CLI, replay, scheduler and deployment belong to Tasks 17-18.
