# Task 17 live-fix: genuine conflicting canonical duplicates (E-REDES 2026-11-01)

2026-11-12 · scoped fix on top of `6cf6777` · Task 17 NOT closed by this change

## The genuine condition

The controller's full Apr 1 – Nov 11 f0nix run (226 real JSON responses) failed the entire
~64k-observation batch on the publisher's canonical duplicates of 2026-11-01: the portal
doubles the 01:00/01:15/01:30/01:45 UTC stamps with **conflicting** dgm/pre/total values per
copy (e.g. dgm 980304.0 vs 1020794.0 at 01:00). Raw evidence: controller run DB raw_fetch
id 216 (fetched 2026-11-12T21:38:32Z, HTTP 200, sha 6bc99c93…, 17244 B). No null numbers in
any of the 225 day payloads. One stamp can never be picked as "the fix", and dropping the
whole day (or history) is the false alternative.

## Fix (minimal, principled)

One condition changed in the source, one sentinel added in the verifier. `validate()` stays
the only authority on duplicate periods; no dedup/aggregation/special-case invented anywhere.

- `ingest/sources/eredes.py` — the equal-timestamp RAISE (`t_raw <= prev`) is removed; only
  strict backward ordering (`<`) still fails closed. Canonical duplicate rows are handed
  **unchanged** to `validate()`, whose existing `duplicate_period` rule quarantines EVERY
  occurrence — zero duplicates served, no copy chosen. Every native guard (canonical stamp,
  Gregorian, unit/type/label metadata, window identity, page completeness, number-token
  grammar, wall-time echo shape) is untouched.
- `ingest/verifiers/eredes.py` — a stamp repeated in one CSV day file is marked **ambiguous**
  for that day: neither copy is served (no last-row overwrite, the first copy is retracted),
  items at the stamp answer `observed_text=None` (mismatch, like not-found), and unaffected
  stamps of the same day still verify. No import from the collector; static
  allowlist/subprocess independence checks still pass.

## Fixtures (genuine, no fabrication)

- `tests/ingest/fixtures/eredes/nov1_window_json.body` — UNMODIFIED raw-store bytes of
  raw_fetch id 216; URL/params/fetched_at/status/sha/bytes copied verbatim from the run DB
  (no invented timestamp).
- `tests/ingest/fixtures/eredes/nov1_window_csv.body` — ONE fresh capture of the same day on
  the verifier channel (exports/csv, lang=pt & timezone=UTC & where=Nov 1): HTTP 200, 8143 B
  of the 200 KB cap, 0.411 s of the 20 s deadline, timeout 10 s, 0 retries;
  sha b5c7e77d…, fetched 2026-11-12T21:47:14Z.
- `MANIFEST.json` — addendum only (`addendum_2026-11-12_nov1_duplicates` + two new sets);
  no previous set was rewritten.
- Ground truth (asserted in tests): 97 rows per channel, identical stamp sets, byte-identical
  value tokens; 89 unique stamps + 4 doubled stamps (consecutive copies, conflicting values).

## Tests (green)

New `tests/ingest/test_task17_live_fix.py` plus updated inverted expectations in
`test_source_eredes.py` / `test_verifier_eredes.py`:

- fixture proves its own property (97 rows, both copies of all 4 pairs with exact tokens,
  counts **derived** from the bytes: 97 rows → 89 valid / 8 quarantined per series);
- source parses the genuine day without raising; both versions of every duplicate reach
  validation with exact tokens; validator quarantines all 8 rows × 3 series as
  `duplicate_period`, serves 89 × 3 = 267 observations, keeps every other cell verbatim;
- unchanged fail-closed guards ON the Nov 1 fixture: out-of-order records, quoted number
  token, HTML answer;
- verifier on the genuine CSV: 5 named actual samples (market/special/total across
  00:00/00:15/02:00/12:00/23:00) verified with exact tokens; every ambiguous stamp × series
  → `observed_text=None`; one explicit ambiguous `BlindItem` (01:00) → not found, per-item
  evidence envelope intact; absent 23:45 → also None;
- full registered `run_with_refetch` over the fixture pair: `verified` in one run,
  `n_written=267` / `n_quarantined=24` (all derived), both copies of each stamp quarantined
  per series, nothing at a duplicated stamp in `observation`/`served_observation`,
  267 served, verification sample 50/50 passed, raw evidence archived.

Verification: `pytest tests/ingest/` = **1331 passed, 7 deselected** (live-only); ruff clean
on touched files. Existing duplicate expectations were strengthened (quarantine of BOTH
copies, no copy chosen), not deleted.

## Explicitly out of scope (unchanged)

No DB/pipeline/operations/grouping/migration change; no helper imports from source in the
verifier; previous publisher fixtures never rewritten; Task 17 stays open. The pre-existing
AGENTS.md/CLAUDE.md tool-gate edits remain uncommitted awaiting owner approval.

Blast radius (gitnexus, worktree `prumo-pipeline`, indexed at the fix commit base):
EredesSource/EredesVerifier risk LOW, no affected processes; detect-changes: 2 source
symbols + verifier check, flows "Parse → _loads/_text", "Check → Get" only.
