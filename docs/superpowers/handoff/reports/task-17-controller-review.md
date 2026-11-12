# Task 17 controller acceptance and final cleanup

Updated 2026-11-12. Operational code d05e24b remains accepted. Task 17 is now COMPLETE after the final cleanup at f8cb9b0, documentation-only fixes at 062fd65, independent specification/quality approval and scoped re-reviews. Controller normal suite and fresh requirements-only CI rehearsal each passed 1,382 tests with seven live tests deselected. This report retains the prior operational/live evidence; final cleanup evidence is in task-17-cleanup-controller-review.md. No main merge or deployment.

## Operational contract accepted

The public CLI supports run, status, verify, import-legacy (CSV), replay, capture, and explicit recorded-bundle runs. Operations, presentation, persistence and HTTP/file infrastructure remain separate. Normal ingestion and replay call registered run_with_refetch; verify targets one existing pending non-legacy run with the registered verifier. Inactive series are not fetched. DGEG is visible as blocked even with all entries inactive; redistribution eligibility remains separate from technical verification.

World Bank runs one dataset per native indicator, so one export outage does not stop healthy indicators. A single registered WorldBankVerifier accepts an explicit, validated and copied indicator_locales map: GDP growth and unemployment use the reviewed Spanish exporter; the rest use English. No fallback, private-registry mutation, rounding or source substitution.

Migration 0007 enables only active, licensed World Bank legacy rows through legacy_served_source:worldbank=1. The global legacy_served setting remains zero. Legacy rows retain kind=legacy-unverified, their original timestamps and NULL raw provenance. Failed fresh runs never become eligible or replace good data. Migration 0008 labels live, recorded and legacy input. Migration 0009 adds blocked-stale/stale_refusal with populated-schema preservation independently checked.

Manual capture records real statuses, final URLs, exact bytes, hashes and original timestamps. Loading validates every file before opening a DB; recorded mode has no network fallback. The original collector fetch time is retained in both raw_fetch and observations; attempt and verification clocks remain current. Staleness is checked by dataset using collector-backed receipts, plus an atomic per-observation guard. Both loader and pipeline independently reject future receipts under one five-minute skew policy. Capture uses a killable HTTP worker with a whole-phase deadline, physical request accounting and streaming body bounds.

Operator instructions: /home/joao/projects/prumo-pipeline/docs/data/manual-refresh.md. The capture command on another machine/network is the supported manual route. A bare browser ZIP without a receipt is preserved but is not silently assigned an HTTP status or treated as a supported bundle.

## Fresh E-REDES historical acceptance

At d05e24b, the actual CLI run eredes --from 2026-04-01 --to 2026-11-11 through f0nix egress completed in verified: 64,479 observations, 24 duplicate_period quarantines, 50/50 exact sampled matches, 64,479 eligible rows in the isolated test DB. There were 274 real HTTP responses in 302.27 seconds, within the enforced controller request/time budget; per-request timeout was ten seconds with no HTTP retry. Covered native stamps: 2026-04-01T00:00:00+00:00 through 2026-11-11T00:00:00+00:00. This is the publisher's available coverage, not a claim that every quarter-hour grid cell exists.

The first full run at 6cf6777 failed validation without writing observations: the publisher repeats four UTC stamps on November 1 with conflicting values. Fix d05e24b passes canonical duplicates unchanged to the existing validator, which quarantines both versions, while strict backward ordering still fails. The independent CSV verifier retracts the first duplicate and marks the stamp ambiguous, without aborting unaffected rows from the same day. No value or timestamp was repaired and no duplicate was chosen. Genuine November 1 JSON/CSV fixtures and both scoped reviews are retained.

Every stored observation/value/raw-fetch tuple was independently checked against the original JSON bytes; every excluded conflicting cell was matched to its original duplicate token. All 50 verification comparisons and 47 evidence envelopes replayed offline. A separate socket-banned audit re-parsed the original 48 CSV/metadata responses through the registered independent verifier and recovered the same exact values/units/flags.

## World Bank continuity and manual acceptance

At 6cf6777, the real original legacy CSV import retained 161,263 observations. Under the new scoped permission, 44,487 active, unit-valid legacy World Bank observations were eligible; no other source was enabled. Latest usable legacy World Bank timestamp was 2026-03-15T20:50:53Z. The raw export also contains 195 April 6 World Bank rows, all without units; their existence does not justify attaching guessed units or claiming an April date for the eligible legacy set.

A controller-created bundle repackaged only the original JSON/Spanish CSV responses with precise original request timestamps for GDP growth and unemployment. No timestamps were invented for the other sixteen CSV archives whose older recovery manifest lacks precise receipt times. The actual CLI imported both complete indicator/geography groups with the network forbidden: 4,975 fetched observations, 2,153 publisher-null quarantines and 108/108 exact sampled matches. All 161,263 legacy rows remained byte-for-byte unchanged. The served view then contained 4,975 independently verified recorded observations plus 39,686 retained legacy observations; fetched values superseded legacy only for the same series/period. Original JSON retrieval dates remained 2026-11-12T10:41:18.426378+00:00 and 2026-11-12T10:41:28.950981+00:00, not the manual import time. A separate socket-banned audit re-parsed both original CSV ZIPs through the registered verifier and recovered all 108 comparisons exactly.

A bounded real f0nix population-group ingestion also passed: 54 registered geographies, 3,564 observations, zero quarantine, 100/100 exact sampled matches, two actual HTTP responses in 2.627 seconds. This proves that group operationally, not fresh availability of all World Bank exports. Prior full-source CSV timeout/502 evidence remains valid as historical observations, without a claim about their permanent cause. File-based continuity no longer depends on every export being simultaneously healthy.

## Live capture and offline replay acceptance

The real default capture HTTP worker captured one full E-REDES day, November 10, without opening the configured DB. Three distinct exact publisher responses were sealed (identical metadata receipts deduplicated under the documented policy). The resulting bundle was imported into two independent DBs with the network forbidden and different fresh random seeds. Each replay verified 288 observations, zero quarantine and 50/50 exact samples, with all original value/provenance tuples and receipt times preserved.

These manual and population checks ran at 6cf6777. The later d05e24b change is confined to E-REDES canonical duplicates and its tests/fixtures; it received independent scoped specification and quality approval. The final whole suite below includes every change.

## Final verification

.venv-ci/bin/python -m pytest tests -q: 1,335 passed, 7 live deselected, 3 warnings in 310.26 seconds at d05e24b. The live acceptances above were executed separately. Ruff on the touched operational/source/verifier/test paths passed; this is not a claim that every old repository path is lint-clean. SQLite integrity_check and foreign_key_check passed on the acceptance DBs.

Durable evidence is under /home/joao/projects/prumo-pipeline/docs/superpowers/handoff/reports/evidence/task-17/. manifest.json records the hashes, sizes, code revisions and member counts of the controller-created capsules. Every member was re-read and every content-addressed raw body rehashed. These are audit capsules, not publisher archives. The World Bank continuity capsule intentionally omits the all-source legacy DB; it includes the permitted World Bank bundle, raw evidence, status and report instead. Other-source legacy values were not republished in this artifact. Raw-fetch absolute paths in snapshot DBs are historical capture paths; relocate by source/hash when replaying from a capsule.

## Final cleanup acceptance and remaining boundaries

The owner requested continuation and the exact legacy cleanup completed without a tool refusal. The base.py entry in the previous deletion proposal was wrong: dadosgov.py and habitacao.py use bare local imports, so base.py was preserved. The superseded collectors/orchestrators were removed, unused dashboard fixtures retired, and CI detached from DuckDB seed creation and accidental live-test selection. All data/archive/seed files, publisher evidence and retained collector implementations remain unchanged. Independent spec/quality and documentation-fix re-reviews passed; see task-17-cleanup-controller-review.md for the two full-suite results and exact preservation checks. No further source recovery loop was launched.

GitNexus generated changes to protected AGENTS.md and CLAUDE.md during prior indexing. Attempts to revert only those generated hunks were themselves blocked awaiting consent. They remain byte-identical to the cleanup controller intake, dirty, unstaged and uncommitted; do not silently retry via another tool or include them in a feature commit. This protected-file boundary is separate from the now-completed Task17 legacy deletion.

Task 18 scheduler/compose/deployment and Task 19 final methodology/source docs/audit are not started. The new pipeline is not installed in production; the public app remains maintenance-only. Merge into main stays the owner's decision.
