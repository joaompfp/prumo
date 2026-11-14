# Re-review 2: verification, registry and status fixes (Tasks 21, 22, 23)

Branch `pipeline-rebuild`, range f618106..267a487 (HEAD 267a487). Reviewer: adversarial
re-review, read-only on the checkout (only this report written). No subagents.

Scope: Task 21 (`ingest/sampling.py` prumo-sample-v2, `ingest/verify.py`, `ingest/verifiers/*`
reread/request_key/not_compared, bundle-mode live verifier, outage vs mismatch, mandatory
evidence, World Bank E-notation rewrite), Task 22 (registry: native_code uniqueness, unit and
geography labels, `LEGACY_UNIT_SPELLINGS`, `ingest lag`, `seasonal_adjustment`) and Task 23
(status `last_confirmed_current`, `open_db_readonly`, scheduler blocked-once, `static/`
deletion, HEAD handlers).

## Method and independent checks

- Read `sampling.py`, `verify.py`, `verifiers/__init__.py` and the `reread`/`check`/
  `request_key` code of all 8 verifiers, `data_lag.py`, the status staleness code,
  `open_db_readonly`, `pipeline._same_as_previous_verified`, `Db.run_changed_keys`,
  `legacy_import` alias, `app/main.py`, `app/maintenance.py`.
- **Hypergeometric sample size, recomputed independently** with integer binomials
  (`comb(M-D, n) / comb(M, n) <= 0.05`, D = max(1, ceil(0.01 M))), not the code's Fraction
  product: identical to `discovery_size` for every pool size 1..2999 plus 10,000 and 50,000
  (0 mismatches). Spot values: 1,000 -> 258, 2,500 -> 281, 10,000 -> 294, 100,000 -> 298,
  1,000,000 -> 299, 10,000,000 -> 299.
- **sha256 ranking reproduced outside Python**: `printf 'prumo-sample-v2\x1f12345\x1frandom\x1fine.x.PT\x1f2020-01' | sha256sum`
  equals `sampling.rank(12345, 'random', 'ine.x.PT', '2020-01')`.
- **World Bank `_plain` fuzz** (300,000 random tokens: signs, leading zeros, up to 25-digit
  mantissas, up to 30 fraction digits, trailing zeros, E/e, exponents +/-/unsigned 0..400
  zero-padded): all 99,693 tokens the regex rewrites satisfy
  `parse_decimal(_plain(t)) == Decimal(t)` with no exponent left; holds with the decimal
  context precision set to 3 (format 'f' is exact). Every token NOT rewritten (leading '+',
  lowercase 'e', unsigned exponent) is refused by `parse_decimal`, so it fails closed as a
  mismatch, never a silent pass.
- **Monte Carlo of the retry effect** (see I1): BPstat-shaped run (10 series x 431 months,
  1% deterministic defects in history), 1,500 fresh seeds.
- **Registry audit**: every Eurostat series' `seasonal_adjustment` vs the `s_adj` pinned in its
  native_code (0 disagreements; None exactly where the dataset has no `s_adj` dimension);
  one unit label per Eurostat unit code and per WB indicator (holds except the inactive PPP
  pair, intentionally kept).
- Checked live (one HEAD-equivalent GET) that the WB CSV export URL does not redirect, so the
  `reread` exact-URL rule matches what `check` records.

## Strengths

- **The sample design is sound and the documented arithmetic is exact.** `discovery_size`
  matches an independent integer-binomial computation everywhere tested. The proof that steps 3
  and 5 cannot weaken step 4 is correct: removing step-3 rows from the pool shrinks M, and each
  factor (M-D-i)/(M-i) is increasing in M; if a defect fell in a step-3 row it is caught anyway.
- **Ranking is reproducible and version-independent** (sha256 over a documented string,
  verified with coreutils), the seed is 63 bits from `secrets`, drawn after the run's data is
  written, and stored with the design summary.
- **Request-key closure turns six sources into censuses** at no extra HTTP cost (Eurostat TSV,
  WB ZIP, FRED page, OECD CSV per series, REN chart-month, E-REDES day CSV). This is the
  strongest possible answer to B-I1 for those sources.
- **No path marks a crash/outage/mismatch verified.** Outage (`VerifierUnavailable`,
  `OSError`, which includes all `requests` transport errors) sets a whole-run note, so every
  item fails; malformed results, wrong count, non-exact `str`, missing evidence, undeclared
  unit/flag omission all fail; `passed = bool(rows) and not bad`. Outage stops refetch and
  escalates; drift and mismatch refetch.
- **`reread` is a genuine re-read in all 8 adapters**: each re-parses the archived bytes
  (TSV, ZIP inside the envelope, CSV, HTML, JSON envelopes) and shares its decision helper with
  `check` (`_one`, `_result`, `_decide`, `read_csv_evidence`, `read_table_page`), and replay
  requires an exact match of key + text + decimal + unit + flag before re-deciding. The
  per-adapter forged-claim test proves an echo would fail.
- **Bundle mode verifies over live HTTP by default**; the pinned channel is explicit, recorded
  (`verifier_channel='pinned-bundle'`), refused for live input, and single-attempt.
- **E-notation rewrite is exact** for every token class it accepts, and fail-closed for the rest.
- **Seasonal adjustment** is mechanically derived from the pinned `s_adj` for 304 Eurostat
  series with no disagreement; INE values come from sha-pinned fixtures.
- **Legacy alias is narrow**: one former label for one series id, applied only on legacy
  import, never a conversion; the real-data import is byte-for-byte equivalent.
- **`last_confirmed_current` matches the pipeline's short-circuit rule exactly**: status uses
  the immediately previous run of the same dataset_key in any state (`runs_overview` lists all
  runs), as `_same_as_previous_verified` does, and requires that run (and every run back to the
  one that wrote rows) to be still `verified`. A withdrawn or failed matched vintage confirms
  nothing. Legacy rows never confirm currency.
- **`open_db_readonly`** refuses missing files, non-Prumo files and schema skew in both
  directions, uses `mode=ro` + `query_only`, never migrates, and leaves no sidecars when no
  writer is running.
- **Static deletion is clean**: the maintenance page references only
  `/static/images/prumo/favicon.svg`, which is the single remaining tracked file; the mount,
  Dockerfile `COPY static/` and `.dockerignore` rules stay, so the docker contract holds.
  `GET`/`HEAD` both answer on `/healthz` and the catch-all.

## Issues

### Critical

None found.

### Important

**I1. The 95%/1% guarantee holds per verification, not per served dataset: refetch and
scheduler retries re-draw with fresh seeds, so a deterministic defect eventually passes, and
the identical-payload short-circuit then keeps it served.**
- **Where:** `ingest/verify.py:402-423` (`run_with_refetch`: each attempt is a new run,
  `_verify(..., seed=None)` draws a fresh seed, nothing from the failed attempt is carried
  forward); `ingest/sampling.py:28-35` and `docs/data/methodology.md:131-138` (the
  statistical statement); `ingest/pipeline.py:305-309` (short-circuit onto the passed run).
- **What:** a parser defect is deterministic: the refetched bytes re-parse to the same wrong
  cells. Each attempt independently misses them with probability <= 5% (for INE/BPstat, where
  step 4 matters). Within one `run_with_refetch` (3 attempts) the chance that a dataset with
  1% wrong history cells is served is up to 1 - 0.95^3 = 14.3%. Monte Carlo on a BPstat-shaped
  run (10 x 431 months, 43 wrong history cells): 3.1% pass per attempt, **9.1% within 3
  attempts**. The scheduler then retries failed datasets on its own backoff, each retry being
  another 3 draws, so over days the probability of eventually serving the defective data tends
  to 1. Once one attempt passes, the next identical payload short-circuits to `verified` with no
  verification, so the lucky pass is permanent until the publisher changes the bytes.
- **Why it matters:** the methodology says "an error rate of 1% or more in the unverified
  remainder would have been found with at least 95% probability". For served data that is not
  true under the retry policy. The census sources (Eurostat, WB, FRED, OECD, REN, E-REDES
  within a day) are unaffected because their closure is deterministic; INE and BPstat are.
- **Fix (small):** make known mismatches sticky. When a dataset_key's latest verification
  failed on value mismatch (not outage/drift), add those (series_id, period) keys to the next
  attempt's must-check set (new reason, e.g. `previously-failed`, stored in `sample_design`),
  following the chain back to the last verified run of that key. A deterministic defect then
  fails every attempt; a transient fetch glitch still clears. Alternatively state the
  per-dataset bound honestly (e.g. size step 4 at alpha/3 and document scheduler retries).

### Minor

**M1. Verification does not run `reread` at verify time, so a "verified" item is not
guaranteed to replay.** `ingest/verify.py:172-180`. `check` and `reread` share helpers, which
makes divergence unlikely, but nothing enforces it at the moment the run is accepted (e.g. a
recorded final URL that differs from the exact template would make every World Bank item fail
replay; checked live that it does not redirect today). `reread` is pure and cheap per response:
call it for each item in `_verify` and fail the item on disagreement, so every stored match is
replayable by construction. Also reject `evidence == b""` (only `None` is refused,
`verify.py:254`).

**M2. Methodology says n "tends to 298"; the limit is 299.** `docs/data/methodology.md:128`
(and the comment in `tests/ingest/test_sampling.py:54`). `discovery_size(10**6) = 299`
(ln 0.05 / ln 0.99 = 298.07, so the binomial limit is the next integer, 299). Cosmetic, but it
is the published audit statement.

**M3. `_plain` has no bound on the exponent.** `ingest/verifiers/worldbank.py:113-121`. A
single cell `1E+999999999` (12 bytes inside a capped ZIP) makes `format(Decimal, 'f')` build a
~1 GB string. Publisher-controlled input only, so low likelihood; cap the exponent (say
|exp| <= 400) and raise `ValueError` (drift) above it.

**M4. `ingest lag` takes `MAX(period)` over fetched rows of every run state, withdrawn and
failed included.** `ingest/db.py:184-190`. A withdrawn run whose parser produced a wrong future
period (the very reason runs get withdrawn) masks a frozen dataset until real time passes that
period. Exclude `withdrawn` runs at least; the report is advisory, so this is minor.

**M5. `last_confirmed_current` treats a `pinned-bundle` (non-audit-grade) verification as
confirmation, and status does not show the channel.** `ingest/status.py:176-206`,
`ingest/db.py:353-362`. A recorded import verified only against its own bundle reads "fresh".
Either exclude pinned-bundle runs from confirmation or show `verifier_channel` per dataset.

**M6. The `immutable=1` read-only open is decided by a non-atomic `-wal` existence test.**
`ingest/db.py:562-563`. Documented as a residual edge and harmless to the database, but the
realistic trigger is a deploy: the scheduler restarts, migrates (0012 rebuilds `event`) and
can checkpoint into the main file while a status read is in progress, which SQLite documents
as possible wrong results or `SQLITE_CORRUPT` for the reader. In serve mode the scheduler
holds its connection for the process lifetime, so the window is only scheduler restarts and
manual CLI writers. Acceptable; consider retrying once with plain `mode=ro` on
`sqlite3.DatabaseError` so a transient corrupt-read error does not surface as a broken report.

**M7. Cross-source geography is now inconsistent for Greece.** Eurostat active series use `EL`
(11) and World Bank uses `GR` (10); the EU aggregate is `EU27_2020` vs `EU`. C-I2 fixed
consistency inside Eurostat only. Nothing joins on `geography` yet, but the future UI will;
record the convention (publisher code vs ISO) before it does.

**M8. "replay" names two different things.** The CLI `replay --from` is a fresh re-fetch
(`ingest/cli.py:40`), while the audit replay (`replay_check`) has no CLI entry point. An auditor
cannot replay a verification item without writing Python. Add `verify --replay <item_id|run_id>`
or document the API call in operations.md.

**M9. `seasonal_adjustment` vocabulary is mixed.** Codes (`SA`, `SCA`, `NSA`) for
Eurostat/INE/FRED, prose (`Calendar and seasonally adjusted`) for 5 OECD series. Reported in
the Task 22 report as verifier-bound; still worth a canonical enum before the field is shown.

## Declined to judge

- Whether INE's indicator names (0011889 "ajustado de efeitos de calendário e de
  sazonalidade" -> SCA, 0007983 -> SA) match INE's metadata beyond the committed fixtures; not
  re-fetched (INE rate-limits).
- Whether `None` (rather than `NSA`) is right for HICP and annual national-accounts datasets
  without an `s_adj` dimension; None is the conservative choice and not wrong.
- Deployment of the `static/` deletion: CLAUDE.md says `static/` is bind-mounted `:ro` from
  `~/docker/stacks/web/images/prumo`; if that tree is synced without deletion, the legacy
  files stay on disk and are still served. An ops check at deploy, not a code issue.
- Live tests (not run, by instruction) and per-adapter publisher parsing details.
- B-M2, B-M4, B-M6, B-M7 were out of Task 21's scope and remain open as previously reported.

## Test run

`.venv-ci/bin/python -m pytest tests/ingest -q -p no:cacheprovider -o addopts="" -m "not live"`
at 267a487: **1523 passed, 7 deselected (live), 2 warnings in 481 s, exit 0.** This matches
the Task 23 report's count.

## Assessment

**Ready to merge: With fixes.** The verification engine, the sample arithmetic, the
reproducible ranking, the E-notation rewrite, the staleness definition, the read-only open and
the static cleanup all hold up under independent recomputation and fuzzing; I found no path to
`verified` from a crash, outage, mismatch or missing evidence. I1 should be fixed (or the
statistical claim restated) before the methodology's 95%/1% sentence is published, because
retries plus the short-circuit let a deterministic defect in INE/BPstat history be served with
non-trivial probability. The minors can follow.
