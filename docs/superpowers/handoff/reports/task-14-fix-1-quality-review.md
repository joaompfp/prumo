# Task 14 fix round 1 — independent SCOPED quality re-review

**Scope:** re-review of fix round 1 (`8afb13c` source / `b1764bd` live test / `8bc06d4` report,
base `7b93ab8`) against the original round-0 findings **I1** (truncation / count / restriction
identity) and **I2** (Unicode DATE), plus the new live test (**M2**). Actual diff + the 15 new
regression tests reviewed; earlier fixtures/plans/reports not re-read.

**Verdict: REQUEST_CHANGES — one blocker (P1, I1 restriction identity).**
Everything else probed clears (23/24 independent probes; failure reproduced below).

## Blocker

### P1 — unreviewed archived *params* keys fail open on page-1 archives (`ingest/sources/fred.py:325`)

```python
if set(params) > allowed or "series_id" not in params:
    raise ValueError(f"FRED {what} archived params drifted: {params!r}")
```

`set(params) > allowed` tests **strict superset**, not "params has keys outside `allowed`".
It only fires when params already contains *every* reviewed key plus extras. A first-page obs
archive legitimately lacks `offset`, so `{series_id, file_type, limit, <EVIL>}` is **not** a
superset of `_OBS_PARAMS` and the check never fires. The fix hardened only the URL side with
the correct operator (`ingest/sources/fred.py:343`, `if not set(q) <= allowed`); the params
side kept the pre-existing wrong operator (present at `7b93ab8:253`, untouched context).

**Repro** (read-only, fixture bytes + sentinel key, scratch script
`~/.hermes/cache/scratch/task14fix1_qr_independent_probes.py`):

- params `{series_id, file_type, limit=100000, frequency="m"}` + genuine URL/body → **parse
  accepts 561 rows** (no exception).
- params `{..., observation_start: "2010-01-01"}` + a self-consistent restricted obs envelope
  (201 rows, `count=201`, extent `2010-01-01..`) → **parse accepts 201 rows**; 360 periods
  (1980-01..2009-12) silently gone — I1's exact restriction-identity case. The new
  extent/count machinery cannot catch it: the tampered envelope reconciles with itself. The
  params line is the *only* guard and it is broken in this branch.
- Same with `units="chg"`: accepted (transformed values promoted as the metadata's units).
- Control probe with params `{..., offset: "0", frequency: "m"}` → correctly rejected
  (superset branch works), confirming the operator is the defect, not the policy.

fetch() never emits such params, so exploitation needs a tampered/drifted archive — the exact
threat class the fix claims to close ("archived url/params identity is strict: unreviewed …
fail closed") and the class its own URL-side regressions target.

**Fix (one line):** `if not set(params) <= allowed or "series_id" not in params:` (equivalently
test `set(params) - allowed`), plus a regression test with an extra params key on a no-offset
obs archive. No genuine archive is affected (fetch params ⊆ allowed by construction).

## Cleared by concrete probes (23/24 pass)

- **I1 truncation/count:** truncated single page (300 rows, `count=561` intact) → rejected;
  missing tail page → rejected; page-2 count drift `561→562` with accumulated ≤ new count →
  rejected at the ledger (parse **and** fetch paths); repeated offset 0 → rejected;
  `assert_complete` catches zero-page and short archives. Genuine archive parses (control).
- **I1 URL identity:** unreviewed `&frequency= / &units= / &window=` URL keys → rejected;
  duplicated `series_id` (same value) → rejected; URL/param limit disagreement → rejected;
  URL key absent from params → rejected; restricted `observation_start/end` extent echoes with
  rows outside → rejected. Broad `1600-01-01..9999-12-31` genuine extent accepted (containment,
  not endpoint equality) — verified against fixture bytes.
- **I2 Unicode/Gregorian:** Arabic-Indic row date appended (`2026-٠١-01`, count+1) and aliased
  in-place of a genuine row → rejected; Unicode in obs `realtime_end`, `observation_start`,
  metadata `last_updated` → rejected; ASCII-but-impossible `9999-02-30` and year `0000` →
  rejected; values returned verbatim (no normalization) confirmed by reading `_date`.
- **PageLedger health:** no infinite-pagination / no-progress hazard — per-page check
  `offset + len(rows) <= count` plus contiguous offsets means `expected_offset` can never
  exceed `count`, non-progress on an empty page raises `FredRequestError` (probed fetch-side),
  and completion is exactly `expected_offset == count`. Fetch and parse consume the same pin.
- **M2 live test:** negative control is sound, not self-masking. Row-count/period pins are
  derived from publisher-declared `count` and the **independent `/fred/series` endpoint's**
  metadata extent — not solely from re-parsing obs bytes with the same parser. Fixture check:
  meta extent `1992-01-01..2026-09-01` equals first/last value dates; 417 values + 144 `.` =
  561 = declared count, so a wrong DB (dropped/extra rows, shifted range) cannot match both
  pins. Docstring correctly scopes 120 s as per-request with retries=0 (no whole-phase
  deadline claimed); served=0 licence gate, 120 exact verifier comparisons and the keyless
  HTML channel are unchanged. Controller's fresh f0nix run (12/12 verified, 5004 rows,
  1728 quarantined, served 0) is consistent with this; I did not re-run the live suite (no
  network, no owner key) — that remains controller acceptance evidence.

## Deferred MINORs (accepted, not blockers)

- Verifier interior absence / sampling coverage remains as accepted in round 0 (explicitly
  deferred by the brief; unchanged by this fix).
- Informational: `_observations` does not check `len(rows) <= limit`; harmless (params↔payload
  limit pin + count reconciliation prevent any coverage loss). No change requested.

Task 14 is **not** complete pending the P1 fix + regression test and a re-review of that diff.
