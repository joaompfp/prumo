# Task 16 quality review — E-REDES source/verifier + PT15M migration

Verdict: **APPROVED** (code, read-only review of `5feb13f`, diff `03639ee..5feb13f`; three minor
findings, none reachable as a bad served output in the real run flow; live E-REDES gate stays
controller-owned and unrun; task not marked complete by this review)

Reviewer independence: no code in the diff is mine. Scope per controller: meaningful
correctness/security/memory/idempotence/provenance/per-request-identity issues only; probes run
offline from the genuine fixtures (no network), under scratch `t16-qr-lz9x`, `.venv-ci` Python.

## What was verified good (with own probes, not report trust)

- **Fixture integrity and echo consistency (offline)**: all three fixture bodies re-hash to the
  MANIFEST sha256/bytes; the genuine JSON window (96 records, `total_count==results`) has exact
  `dia/mes/ano/date/time` echoes of `datahora`, strictly ascending quarter-hour UTC spelling, no
  duplicate timestamps; the CSV window re-checks identically; **all 288 value tokens byte-identical
  between JSON and CSV**; metadata labels/types/licence (`Market (kWh)` etc., CC BY 4.0, E-REDES)
  match the constants; no duplicate metadata field names.
- **Targeted suite re-run**: `pytest tests/ingest/test_source_eredes.py test_verifier_eredes.py
  test_migration_pt15m.py test_registry_eredes_units.py test_models.py -q` → **179 passed**
  (44 source + 22 verifier incl. named exact samples across fields/times, duplicate-key /
  total_count-drift / missing-page / quoted-number / noncanonical-ts / HTML-200 / licence-drift
  rejections, migration atomicity R1 + raw-spelling R2, registry-metadata pairing).
- **Cross-run preserve-previous-good (probe P1)**: run1 verified+served 288 rows → tampered run2
  failed-verification → served view still returns exactly run1's rows (ids 1..288,
  `1097652.0` verbatim at 23:45Z); a byte-identical rerun after a *failed* run is **not**
  short-circuited (full reprocess, `n_written 288`).
- **Per-request identity / provenance**: pages grouped per (dataset, exact `where`), offsets must
  be contiguous multiples of one pinned `limit` (`eredes.py:307-317`), `total_count` drift across
  pages rejected, `RawRow.response_index` points at the page response and the out-of-range guard in
  `pipeline.py:127` exists; fresh params dict per page (no aliasing); metadata mandatory
  (`n_metadata`, line 303). Fetch-side loop bounds checked: `offset+limit > 10000` raises instead
  of truncating (`eredes.py:266`).
- **Migration 0006**: view text recreated **verbatim from 0005** (diffed: identical); no indexes
  or triggers on `series` exist besides the two recreated observation triggers, so the rebuild
  loses nothing; FK OFF/ON + `foreign_key_check` atomicity independently re-probed by the R1/R2
  fix re-review and its named tests pass here; `open_db` no longer leaks the WAL handle on failed
  migration (db.py).
- **Verifier independence**: `register_verifier` AST allowlist + `assert_verifier_independent`
  subprocess pass; the verifier duplicates constants on purpose and never imports parser code;
  evidence envelope (`eredes-csv-evidence` v1) carries exact bytes/final URL/actual status of CSV
  + metadata per item, raw-store integrity-checked, `replay_item` re-decides offline (tested at
  lines 218-237). Comparison is exact Decimal; unit-label drift (`MWh`) and value tamper
  (`1097653.0`) both flip to failed-verification with nothing served; licence gate contrast
  (CC BY served vs REN-style blocked) tested.
- **Housekeeping**: `ruff check` on all touched files clean; old migrations untouched;
  `core.yaml`/`core.proposed.yaml` eredes blocks byte-identical; git HEAD verified `5feb13f`.
- Memory: fetch is a generator (one ~17 KB page/day), parse bounded by the window; per-item
  evidence duplicates the same two bodies but the raw store is content-addressed (sha-path),
  so 50 items store one copy.

## Findings (all minor; no REQUEST_CHANGES)

1. **Verifier metadata parse is asymmetrically lax** — `ingest/verifiers/eredes.py:138` uses
   plain `json.loads(meta_body)`: duplicate JSON keys are accepted last-wins, while the collector
   rejects any duplicate key via `object_pairs_hook` (`sources/eredes.py:86-101`). Probe P2:
   metadata with a duplicated `"publisher"` key is **accepted** by `EredesVerifier.check` (then
   passes the `publisher`-unasserted verifier path — it only checks `dataset_id` + labels) but
   **rejected** by the collector parse of the same bytes. Reachability is low (the verifier
   fetches the bytes live itself), but the fix is a local 6-line hook duplicated per the
   deliberate-duplication doctrine; a markup precheck like the collector's would also improve the
   error (currently fail-closed via JSONDecodeError only).
2. **Parse has no cross-window coverage notion** — `sources/eredes.py:272-368` asserts
   completeness per (dataset, `where`) day group only. Probes: metadata-only input returns
   zero rows with **no error** (P3; the run-level all-empty rule still classifies
   failed-validation in `pipeline.py:139`), and a 3-day explicit window parsed from a response
   list missing two days' pages yields 96 rows/series silently (P4). Unreachable inside
   `run_dataset` (fetch raises or the non-2xx is classified before parse), but offline raw-store
   replay with a dropped page file would produce a silently holed series. Hardening, not
   regression: reconstruct the expected day set from `self.days` when present and fail on gaps.
3. **Default window uses the host-local date, not UTC** — `sources/eredes.py:204`
   (`today or date.today()`). Probe P5: with `TZ=Pacific/Kiritimati`, `date.today()` shifts one
   day and the "today partial/never requested" invariant breaks — a still-running UTC day enters
   the request; since that day's `total_count` matches its partial results, parse would accept it
   (self-heals via the 3-day overlap; verified previous-good untouched). On the PT production host
   this is reachable nightly during WEST (23:00-24:00 local). One-line fix:
   `datetime.now(timezone.utc).date()`.

## Accepted-by-design caveats (no action)

- Window "completeness" is `count == total_count`; a *partially published* day is accepted because
  both channels show the same partial set. Detected on neither channel by construction; mitigated
  by the daily 3-day overlap (later vintages supersede). Worth one line in the T17 scheduler notes.
- Verifier `_PERIOD` is structural-only; a non-quarter minute item resolves to
  `observed_text=None` → mismatch (fail-closed, never a pass).
- Genuine echo/UTC fixture evidence is one winter UTC day (2026-11-10). Summer-window genuine
  evidence was out of network budget; DST-adjacent spellings are covered synthetically at the
  `normalize_period` level, which is the right layer for them.
- `_migrate` interpolates `f.stem` into SQL (pre-existing pattern, migration filenames are
  glob-restricted and repo-trusted); noted, unchanged by this diff.

Task status unchanged: acceptance and the live gate remain controller-owned; dadosgov untouched;
no code, handoff, ledger or plan files modified by this review.
