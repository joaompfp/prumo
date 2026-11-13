# Final whole-branch review, Part B: verification

Scope: `ingest/verify.py`, `ingest/verifiers/` (all 8 adapters + `__init__.py` + `independence.py`), `ingest/bundle.py`, and the tests in `tests/ingest/` covering them. Branch `pipeline-rebuild` @ 6b938fd, base `legacy-ui-final` (a18a58a). Reviewer: Part B (read-only).

Method: I read all of `verify.py`, `verifiers/__init__.py`, `independence.py` and `bundle.py`, plus the eredes, eurostat and OECD verifiers in full and the channel/lookup sections of the INE, FRED, World Bank and BPstat verifiers. I compared each collector endpoint with its verifier endpoint, and read the pipeline, served-view and CLI paths that touch verification. I ran ad-hoc probes against `_static_violations`, and counted series per dataset group from `registry/core.yaml`. Tests: `.venv-ci/bin/python -m pytest tests/ingest -m "not live"` (result at the end).

## Strengths

- **Fail-closed decision core.** In `verify.py:121-158`:
  - A verifier exception, a wrong result count, a wrong key or order, a non-`ItemResult` result, non-exact-`str` fields (str subclasses and floats included) and `observed_text=None` all count as failures.
  - `passed = bool(rows) and not bad`, so an empty sample cannot pass.
  - The comparison uses exact `Decimal` (`parse_decimal`), never float.
  - Tests cover each of these paths (`test_verify.py:183-384`).
- **Blinding is real.** `BlindItem` carries only the key and the registry spec. The expected value, unit and flag stay in `SampleItem`. `test_echoing_what_it_is_given_cannot_pass` and `test_parser_swapped_periods_with_reordered_verifier_fails` exercise it.
- **The state transition is atomic and compare-and-set (CAS).** The verification rows, the failure event and `transition_run_state(pending -> verified|failed)` run in one `BEGIN IMMEDIATE` transaction. A lost race rolls back and raises `VerificationConflict` (`verify.py:142-157`, `db.py:188-192`), and this is tested.
- **The seed is unpredictable and stored.** It comes from `secrets.randbits(63)`. The sample can be redrawn from the stored `seed` plus `sample_size`: with `size = len(rows)`, `draw_sample` reproduces the same `n_fill` and the same `random.sample`.
- **Each verification item stores every input of the comparison** (expected and observed text, decimal, unit, flag, the key the verifier answered for, the evidence URL and the evidence sha256). `replay_item` re-decides an item with no registry and no network, and integrity-checks the archived evidence bytes.
- **The collector and verifier channels are genuinely different for all 8 sources:**

  | Source | Collector channel | Verifier channel |
  |---|---|---|
  | Eurostat | JSON-stat 1.0 | SDMX 2.1 TSV |
  | INE | JSON `pindica` | bddXplorer HTML table |
  | FRED | `api.stlouisfed.org` JSON | `fred.stlouisfed.org/data` HTML |
  | REN | servicebus JSON | datahub CSV export |
  | BPstat | `data/v1` JSON-stat | `api/series` + `api/observations` |
  | World Bank | API v2 JSON | bulk CSV ZIP |
  | OECD | SDMX-JSON 2.0 | SDMX labelled CSV |
  | E-REDES | ODS `/records` JSON | ODS `/exports/csv` |

  None of the verifiers imports collector code (verified by grep). All 8 verifier test modules call `assert_verifier_independent`.
- **The INE verifier cross-checks each period label against its own `order` end-date** (`ine.py:283-292`). This blunts the risk of sharing `normalize_period` with the collector.
- **The independence guards are layered.** The static check enforces an AST import allowlist, forbidden names and dunder attributes, and transitive closure overlap with the parser. The runtime check runs in an isolated `-I` subprocess with an import blocker and an audit hook that records file opens and module origins.
- **`run_with_refetch` refuses before any fetch** when the source is unverifiable or has no registered or matching verifier. Attempts are bounded (`max_attempts >= 1`). Failed runs are never served: the served view requires `state='verified'`, and previously verified rows stay served (tested).
- **`bundle.py` is careful.** It validates the full manifest and every body before any DB open. It refuses partial bundles, uses exact request-identity pinning with no network fallback, refuses conflicting duplicates, re-checks integrity on every body read, and guards against path traversal and symlinks.

## Issues

### Critical

None found. I found no path where a mismatch, a verifier crash or a malformed result ends in `verified`.

### Important

**I1. When a group has 50 or more series, only each series' latest period is ever verified. Its history is served unverified.**
- **Where:** `ingest/verify.py:82-86` (`must` = the latest row per series; `n_fill = max(size - len(must), 0)`), with the fixed `size=50` at `ingest/operations.py:237` and `verify.py:252`.
- **What:**
  - Eurostat runs as a single group of 329 active series (`operations.py:85-101`).
  - Each of the 18 World Bank indicator groups has 54 geographies.
  - Both therefore get `n_fill = 0`: every verification checks only the newest period of each series, never an older one. The handoff's "949 exact CSV samples" for World Bank is 18 × ~54 latest cells.
  - The test `test_sample_covers_every_series_even_when_size_smaller` (`test_verify.py:104`) asserts this behaviour.
- **Why:**
  - Every run rewrites the full history (`pipeline._write`), and the served view takes the newest row. So all historical vintages of these 1,259 series are served on the strength of latest-period checks only.
  - A parser defect limited to older periods would never be sampled: a period shift in history, a wrong column for back data, mis-mapped revised cells.
  - Spec 6b asks for sampling "stratified by series, period and recency". Period is not a stratum here.
- **Fix:**
  - Size the sample as `latest-per-series + max(k, f(N))` random history items (for example k=50 plus a fraction of N, or a size that gives a stated detection probability), and stratify the fill by period band.
  - Better for these two sources: the Eurostat TSV and the World Bank CSV verifier responses already contain the full history of every sampled series. Comparing every stored observation of the fetched series costs no extra HTTP and turns sampling into full verification there.

**I2. The sample ignores what changed in this run (revisions and new periods).**
- **Where:** `ingest/verify.py:62-89`.
- **What:** the run already knows which observations are revisions (it emits `revision` events in `pipeline._write`) and which periods are new. `draw_sample` treats them like any other row. Apart from the latest period, a revised value is checked only by chance (about 50/N).
- **Why:** revised and newly published cells are the most likely to be wrong, and they are exactly what changes the served numbers. An auditor will ask whether every revised value was checked.
- **Fix:** force every revised observation of the run (capped, with the remainder sampled) into the `must` set alongside the latest periods. Record the reason for each draw (latest / revised / random) in `verification_item`.

**I3. In recorded (`--bundle`) mode the verifier reads the same operator-supplied bundle as the collector, so verification is not independent of the input.**
- **Where:** `ingest/cli.py:247-253`. There `http_for` returns the same `PinnedHttp` for the verifier; the capture side is in `cli.py:476-546`.
- **What:**
  - The bundle manifest is unsigned and operator-writable.
  - `load_bundle` checks only that each body's sha256 matches the manifest, which the editor can recompute.
  - A bundle whose JSON and CSV were edited consistently (with new hashes) therefore passes 100% "independent" verification and is served.
  - Refetch in this mode re-reads the same bytes (`verify.py:289-299`), so "re-fetched" is nominal.
- **Why:** the owner requirement is "verified against the source". Here the verification only proves the bundle is internally consistent. `input_origin='recorded'` labels the run, but the run still reaches the same `verified` state and is served the same way.
- **Fix (preferred):**
  - Run the verifier over live HTTP even in recorded mode. Both supported channels can still answer for historical periods (E-REDES `exports/csv` per day, the World Bank bulk CSV).
  - Fall back to bundle-pinned verifier responses only with an explicit owner flag.
  - Mark the verification row (for example `verification.channel='recorded'`) so the methodology/status output can show it.
- **Fix (at minimum):** document in the methodology that recorded runs are verified against operator-captured bytes, and disable refetch in recorded mode, since repeating it has no effect.

**I4. `replay_item` cannot detect a verifier that misread its own evidence.**
- **Where:** `ingest/verify.py:235-248`.
- **What:** replay re-runs `_row_mismatch` on the stored `observed_text`, `observed_unit` and `observed_flag`, and only checks that the evidence file is intact. It never re-reads the evidence to confirm that the observed token is in those bytes at that key. Re-readers exist for some adapters (`oecd.read_csv_evidence`, `fred.read_table_page`) but are not part of the replay contract, and not every verifier has one.
- **Why:** an auditor replaying a verification gets the verifier's claim compared with the stored value again, not a check of the verifier's claim against the source bytes. A verifier that picked the wrong row or column would replay as "match".
- **Fix:** add a per-verifier `reread(evidence_bytes, BlindItem) -> ItemResult` to the `Verifier` protocol, implemented by every adapter. `replay_item` should then require that the re-read result equals the stored observed fields. Also require `evidence is not None` for every result (`verify.py:182`); today evidence is optional and a verifier can return none.

### Minor

**M1. Unit and flag comparison is optional and silently skipped for many sources.**
- **Where:** `verify.py:226-231`.
- **What:** `observed_unit=None` or `observed_flag=None` means "not compared". In practice:
  - The unit is never compared for Eurostat (`eurostat.py:149`) or World Bank (`worldbank.py:340`).
  - The flag is never compared for BPstat, FRED, REN, World Bank or E-REDES.
- Most of these are defensible: the collectors declare `'normal'` or fail closed on unknown codes, and the Eurostat unit is pinned in the SDMX key. But spec 6b says "comparing value, unit, period and status flag", and the stored row does not record *why* a field was not compared.
- **Fix:** store `unit_compared` / `flag_compared` (or a reason) per item, and summarise per source in the methodology.

**M2. The static independence check is easy to bypass by aliasing, and the allowlist admits reads of the collector's raw payloads.**
- **Where:** `verifiers/__init__.py:254-275` and `:30`.
- **What:**
  - Probes against `_static_violations` returned no violation for `L = logging; L.sys.modules['ingest.sources.eurostat']` (the direct `logging.sys` is caught).
  - `io.open('ingest/sources/eurostat.py')` also passes.
  - `ingest.rawstore.RawStore` is allow-listed, although no verifier uses it, and it can load the collector's archived response bytes.
  - The runtime guard watches opens under `ingest/sources/` only, not the raw store. It also runs only the test entrypoint in a subprocess where parser modules are absent, whereas in production the CLI has already imported them (`sys.modules` is reachable).
- This is documented as "lint" and there is no current misuse, so it is Minor.
- **Fix:** drop `RawStore` from `VERIFIER_INGEST_IMPORTS`; flag any rebinding of an imported module name; add the configured raw-store root to the runtime guard's protected paths.

**M3. Fixed `max_attempts=3` gives no distinct escalation record.**
- **Where:** `verify.py:296-300`.
- **What:** after the last failure no `escalation` event is written. Escalation is only the CLI exit code and report. The loop also does not distinguish "the verifier channel errored" (for example `verifier raised: ConnectionError`) from a value mismatch, so a verifier outage costs three full dataset re-downloads.
- **Fix:** emit `verification_escalated` with all three run ids. Stop refetching when every failure is a `verifier raised`.

**M4. The expected unit comes from the registry at verification time, not ingest time.**
- **Where:** `verify.py:87-88`.
- **What:** a later manual `verify <run_id>` (`cli.py:549-597`) after a registry unit edit compares against the new unit.
- **Fix:** refuse to verify when the registry unit differs from what the run was synced with, or store the unit with the observations.

**M5. `random.Random.sample` reproducibility depends on the Python version.**
- **Where:** `verify.py:86`.
- **What:** CPython does not guarantee the sequence across versions. Replay years later on a different interpreter might redraw a different sample.
- **Fix:** derive the indices from a documented construction (for example sha256(seed ‖ index) ranking), or store the Python version on `verification`.

**M6. The Eurostat TSV parser silently keeps the last of duplicate period header columns.**
- **Where:** `eurostat.py:108` (`dict(zip(periods, ...))`).
- **Fix:** raise on duplicate period headers, as the OECD and E-REDES verifiers do.

**M7. `verify_run` accepts an unregistered verifier.**
- **Where:** `verify.py:92-116`.
- **What:** only `run_with_refetch` and `_cmd_verify` enforce registration (already noted in HANDOFF). One `get_verifier(verifier.source_name) is verifier` check inside `verify_run` would close it.

## Declined to judge

- Whether serving active World Bank `legacy-unverified` rows meets spec 6b ("covers the legacy-unverified import until superseded"): this is serving-gate policy (Part C/D) and an owner ruling. `_cmd_verify` explicitly refuses legacy runs.
- Channel-level independence for E-REDES (same OpenDataSoft backend, different endpoint and format) and OECD (same SDMX API path, different format family): the code is independent. Whether "same publisher database, different serialization" is independent enough is an owner/methodology call, already ruled on in the REN/BPstat precedent.
- Correctness of each adapter's publisher-specific parsing details (INE grid/rowspan, OECD header pinning, FRED HTML): these are covered by per-adapter reviews and recorded fixtures, and re-auditing them is beyond this pass.
- Live-test behaviour: tests marked `live` were not run, by instruction.

## Assessment

**Ready to merge: With fixes.**

The verification engine is sound: it fails closed, compares exact Decimals, is blinded, uses an atomic compare-and-set (CAS) transition and stores a replayable record, and none of the 8 verifiers shares parser code with its collector. Two gaps should be fixed before anyone claims the data "survives a statistician's audit":
- The fixed 50-item sample verifies only the latest period of every Eurostat and World Bank series (1,259 series whose history is served unchecked), and it ignores revisions (I1, I2).
- Recorded-bundle runs are "verified" against the same untrusted bundle (I3).

I4 (replay that re-reads the evidence) is the next most valuable fix for auditability.

## Test run

`.venv-ci/bin/python -m pytest tests/ingest -q -p no:cacheprovider -o addopts="" -m "not live"`: **1397 passed, 7 deselected (live), 2 warnings in 573 s, exit 0.** Ad-hoc probes of `_static_violations` (alias via `L = logging`, `io.open`, `RawStore`) returned no violations, which confirms M2.
