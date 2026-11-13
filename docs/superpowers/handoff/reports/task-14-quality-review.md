# Task 14 FRED — Independent Code-Quality Review

Reviewer: independent quality subagent (after task-14-spec-review PASS, which was not taken as
proof). Scope: `38aad8c..7b93ab8` on `pipeline-rebuild` — `ingest/sources/fred.py` (407 lines),
`ingest/verifiers/fred.py` (375 lines), registry diff, FRED tests/fixtures. Read-only; no
code/handoff/spec edits. All findings below were reproduced by executable probes against the
committed fixtures (scripts under `~/.hermes/cache/scratch/t14_probe_*.py`, run with
`.venv-ci/bin/python`; no network, no real credential read — a sentinel key was used).

## Verdict: REQUEST_CHANGES

No Critical issues (nothing makes the fresh-fetch path serve wrong values; licence gate
`redistribution_ok: false` stays intact). Two Important contract violations in the source
adapter's replay/tamper paths — both contradict the module's own documented fail-closed claims
— plus three Minor items. Fresh ingestion is sound; the weaknesses are in archived-corpus
replay robustness and one ASCII-canonicality hole.

## Important

### I1. `parse()` never reconciles payload-declared extent against rows — truncated/restricted archives ingest silently
`ingest/sources/fred.py:198-230` (`_observations`): per-page checks are one-sided —
`offset + len(rows) > count` raises, but `len(rows) < count` passes, and the values of the
envelope's `observation_start`/`observation_end` (deemed known keys at line 75-77) are never
asserted. `parse()` (lines 386-396) checks page *contiguity* only; it never verifies total
rows == `count`, cross-page `count` agreement, or first-row/last-row vs envelope dates. The
module docstring claims "Fail-closed on: ... count/offset/limit truncation" — false for the
final/only page.

Repro (PALUMUSDM fixture, 561 rows, `count=561`):
- P1: truncated the single observations payload to the first 300 rows, left `count: 561`
  intact → `parse()` **ACCEPTED silently: 300 rows** ("payload count=561 never reconciled").
- P4: set envelope `observation_start: "2010-01-01"` on the untouched full payload →
  **ACCEPTED** (first row is 1980-01; envelope extent unasserted).
- `_identify` (lines 255-258) compounds it: URL query keys absent from `params` are never
  compared, so an archived URL carrying `&observation_start=2010-01-01` is **ACCEPTED**
  ("restriction param unchecked").

Fetch itself loops until `offset >= count` (lines 324-339) so the genuine network path cannot
produce this, and a count *shrink* below the current offset fails closed via the per-page
check — but a shrink that stays >= the final accumulated offset, or any offline-replay over a
truncated/tampered archive, ingests partial history error-free. Because verification items are
derived from ingested rows, missing periods produce no items and no mismatch: coverage loss is
invisible to the value-sampling verifier (I confirmed the engine side conceptually via the
120-of-120 sampling design; observed_text=None only for periods that exist as items). A corpus
rebuilt from raw-store evidence (the documented recovery path) would come out 261 periods
short while looking fully verified. Fix is cheap: track per-series expected extent
(`final expected_offset == count`, cross-page `count` agreement, optional first/last row vs
`observation_start/end`) and reject unknown URL query keys (require `set(q) <= set(params)`).

### I2. `\d` in the source date regex admits Unicode digits — non-canonical period keys escape the dup check
`ingest/sources/fred.py:63` (`_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")`): `\d` is
Unicode-aware on `str`, and `_date` (lines 127-134) keeps the raw text. The parser therefore
emits non-ASCII period keys while claiming (docstring + line 398 comment) "canonical YYYY-MM".

Repro P2: appended a row `2026-٠١-01` (Arabic-Indic month) alongside the genuine `2026-09-01`
tail → source **ACCEPTED** both; emitted `[..., '2026-09', '2026-٠١']`, distinct keys to the
duplicate check, both collapsing to `'2026-01'`/`'2026-09'` at `normalize_period`. Downstream
containment observed (P2b): `validate()` rejects the colliding pair as `duplicate_period`
(both the genuine *and* the alias row quarantined — fail closed, no false value served), and a
lone alias carrying a swapped value would still be caught by value verification. So value
integrity survives via downstream layers, but the source's own trust boundary leaked: a
Unicode-aliased month reached `validate` at all, and alias injection can delete a *genuine*
row via the both-rows rejection (invisible coverage loss, same blind spot as I1). Project
standard (canonical ASCII decimal keys) says the source should never emit it. Fix: `[0-9]` or
`re.ASCII` in `_DATE`/`_LAST_UPDATED`, or assert `s.isascii()`.

## Minor

- **M1. Verifier interior-row removal parses clean (absence-only tamper).**
  `ingest/verifiers/fred.py:317-322,332-334` enforce strict ascending order, no duplicates and
  Date Range *endpoints* == first/last rows. Repro V6: deleting the interior row `2000-06-01`
  from the table HTML → parses clean (416 values, `'2000-06'` silently absent). Consequence is
  bounded: a sampled item for that period gets `observed_text=None` → mismatch → fail closed
  with old verified data preserved; unsampled absence is invisible by design of sampled
  verification. Endpoint removal **is** caught (V1: "table rows run 1992-02-01..2026-09-01"
  vs declared range). Acceptable residual risk; documenting it, not demanding a fix.
- **M2. Live test asserts stale-prone hardcoded current counts.** `tests/ingest/test_live_fred.py:70-74`
  pins `n == 417`, range `("1992-01","2026-09")` and `12*144` quarantines — guaranteed to fail
  the month FRED next publishes, requiring a test edit each cycle. Fail-loud and live-gated
  (`-m live`), so direction is safe; a `>=`/range-or-newer assertion would age better.
- **M3. `_identify`'s query/params agreement is one-sided** (part of the I1 compounding):
  `ingest/sources/fred.py:255-258` only compares keys present in both; keys missing from the
  URL query are fine (params carry identity) but extra URL keys should be rejected for a
  strict archived-identity binding.

## Verified good (probed, no finding)

- **Credential hygiene**: key on wire only; archived `url`/`params` key-free in all 48 fixtures
  (MANIFEST sha256 all match; zero `api_key` bytes in any fixture body/URL outside MANIFEST
  documentation); response echo of the key refused before yield; `_strip_key` post-checks the
  final URL; `FredRequestError` carries only exception type/endpoint/series; `.fred_api_key`
  file never read. Reviewer never touched the real key.
- **Verifier strictness** (repros V2-V5): Unicode-digit table dates REJECTED; duplicate
  periods REJECTED; grouped/otherwise non-plain-decimal tokens REJECTED; `datetime.strptime`
  does not parse Arabic digits at all (roundtrip check is a second lock); truncated pages,
  duplicate metadata rows, header-shape drift, h1/meta/aria triple disagreement all raise by
  construction. `_numeric` keeps tokens verbatim ASCII; missing marker is exactly `'.'`.
- **Source token/type discipline**: quoted-token preservation confirmed; a numeric-shape-odd
  token (`'1e5'`) passes the source but is quarantined `non_numeric` by `validate()` (probe
  P5) — the layer split works. Duplicate JSON keys, markup bodies, the API error shape,
  identity drift, non-2xx, mixed timeouts: all fail closed in code and covered by tests.
- **Registry diff**: 12 active IMF globals with exact publisher units + `seasonal_adjustment:
  NSA`; 8 conservative inactivations incl. MHHNGSP; `redistribution_ok: false` with documented
  UNVERIFIED IMF grant rationale; `verifiable: true` with the data-table channel named.
- **Verifier independence**: reimplements `_native`/`_month_first`/`_numeric`; imports only
  shared infra (`ingest.http`, `ingest.models`, `ingest.verifiers`); no source helpers, no
  blind expected values; single archived HTML response per check carries unit + values
  evidence (schema `fred-table-evidence` v1, b64 body + final URL + status) and
  `read_table_page` is the offline replay path.
- **Evidence bundle/provenance**: 48/48 fixture hashes match MANIFEST; fetch date, statuses,
  final URLs, byte counts recorded; CSV rejection evidence documented
  (`csv-decimal-mismatches.json`).

## Controller's gates

Fix gate and completion stay with the controller; this review closes nothing. Both Important
items are one-to-few-line fixes in `ingest/sources/fred.py` (extent reconciliation in
`parse()`/`_observations` + `_identify` query-key strictness; ASCII-only date regex). Neither
invalidates the spec review's PASS on the fresh-ingestion path, and none of the 12 series'
verified values are affected (the f0nix run's 5004/120-exact results stand); both matter for
the raw-store replay/tamper-resistance story this task is chartered on.
