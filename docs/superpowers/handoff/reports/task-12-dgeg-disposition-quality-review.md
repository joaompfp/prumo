# Task 12B DGEG disposition — independent QUALITY review (APPROVED)

Date: 2026-11-11 · Reviewer: fresh independent quality reviewer · Scope: `869ba6d..fd54d98`,
DGEG safe disposition ONLY (adapter/ingestion still blocked, not reviewed here) · Method:
read-only diff/doc/test inspection + own loader-level probes + own evidence re-hashing +
workbook raw-XML spot checks. No code edits, no commits, no network, no full-suite re-run
(controller's 836-passed/4-deselected run at 136 s and clean ruff are on record and in scope).

## Verdict

**APPROVED.** Preservation, fail-fast exclusion, documentary accuracy and evidence/test
integrity all check out under my own execution. Two small doc-only corrections are listed at
the end (one is the known spec-review minor, independently re-confirmed; one new wording
nit). No blocking findings.

## What I ran and saw (own execution, not report claims)

**Registry preservation (17/17 exact, zero deletions, zero edits)**
- `git diff 869ba6d..fd54d98` registry files = +25/−0 per file; my `load_registry` probe:
  exactly 17 dgeg specs, `all active == False`, every one still
  `(primary, energy, A, PT, decimal='.', native_code='energy-data.db')`; units exactly
  {%, Mtep, Mton CO2e, TWh, ktep, tep/M€, tep/M€'2021, tep/M€2021}. Ids/roles/keys/frequency/
  geography byte-preserved (the diff adds only `active: false` after `native_code`).
- `cmp registry/core.yaml registry/core.proposed.yaml` → identical.
- Sources with `verifiable: false` across the whole loaded registry: **{dgeg} only**.
  `redistribution_ok: false` = {dgeg, fred, oecd, ren} — all pre-existing, untouched by this
  diff. The many other already-inactive eurostat/ine series pre-date this diff (diff proves
  only dgeg additions). No REN/eurostat/INE/bportugal/ERSE/engine changes; changed-file set =
  registry(4) + tests(2) + evidence(7+manifest) + implementer report only.

**Fail-fast exclusion is real, not cosmetic**
- `run_with_refetch` (ingest/verify.py:270-274) raises `SourceNotVerifiable` from the handed
  specs before `get_verifier` and before any fetch — independent of `active`, so a hand call
  with the 17 inactive dgeg entries still refuses (the new test proves exactly this:
  exploding dgeg-labelled doubles + empty `FakeHttp`, `http.calls == []`, zero
  dataset_run/raw_fetch rows).
- I ran `.venv-ci/bin/python -m pytest tests/ingest/test_registry_dgeg_disposition.py
  tests/ingest/test_registry.py -q` → **29 passed in 18.35 s** (6 new + 23 registry).
- The synthetic withholding test is clearly labelled synthetic (no source/verifier/network,
  `synthetic.invalid` URL) and pins fetched+legacy withholding incl. `legacy_served='1'` with
  rows persisting unaudited (2 observations, served 0) — withheld, not deleted; never a live
  DGEG claim.
- Existing-test edit (`flagged == {"dgeg"}`) is a strengthening of the stale blanket
  all-true assertion, not a weakening; it still forces every non-dgeg source verifiable.
  The new file's RED→GREEN history (4 failed pre-change) shows the tests bite.

**Evidence integrity (7 payload files + manifest, no fake full archive)**
- I re-hashed all 7 files: sha256 and byte counts match MANIFEST.json exactly; max 130,573 B
  (dadosgov JSON), well under the 200 KB cap; workbook = original 119,336 B /
  `5f31904a…837be`. The 2.4 MB APN and 13 MB AEN PDFs are correctly NOT committed — both
  derived files open with a `DERIVED EVIDENCE — NOT the raw HTTP response` header naming
  source-PDF URL/sha256/bytes/pdftotext method. The dadosgov entry honestly records
  `http_status: "not recorded in the prior discovery manifest"` instead of inventing a 200.
- Independent raw-XML spot checks against the committed workbook: electricity ktep row
  (sheet2 r21) ends `…4187, 4261, 4349`, and the committed APN derived text (line 106) ends
  `…4 187  4 261  4 349` — the APN-ktep exact-channel claim holds on the tail years I checked.

**Documentary accuracy**
- Reason matrix truthfully distinguishes real partial channels from absence: APN ktep exact
  10/10 for final energy and electricity while flagging the registry Mtep/TWh unit conflicts
  (rows 6, 13 — inactivated for the conflict, "NOT 'no channel'"); CEP 8/10 with explicit
  2021/2022 vintage drift and pre-2015 coverage gap (row 4, "NOT 'no channel'"); vs genuine
  no-mapping/duplicate/misassignment/base-year/representation-policy/weak-independence rows.
- No fraction→percent relabel: row 7's raw `0.64312837828385205` fraction under `0.0%` format
  is preserved with an explicit owner-policy gate; the relabelling recommendation is recorded
  as REJECTED. No invented licence permission ("unconfirmed grant", `redistribution_ok` stays
  false) and no categorical illegality claim (licences-todo.md: "NOT a determination that
  reuse is legally forbidden"). The scoped comment in core.yaml explicitly disclaims any
  "DGEG can never be verified" reading.
- Legacy DGEG import untouched: `ingest/legacy_import.py`, `collectors/dgeg_fuel_api.py` and
  all migrations are outside the diff. See doc correction 2 for the one wording nit.

**Future-CLI requirement (T17/T18)** — recorded, not a defect here: nothing in
pipeline/verify/app consumes `SeriesSpec.active` yet (models.py:194 default only; db sync
persists it), so nothing forecloses the requirement that the future CLI must surface DGEG as
**blocked** (active:false + verifiable:false) rather than reporting a successful run that
silently skipped it. unverifiable.md and the registry comment already pin the scheduling
exclusion; the blocked-visibility obligation lands with T17/T18 (HANDOFF line 54 context).

## Blocking findings

None.

## Small doc corrections (doc-only, not new policy; controller may fold into next registry touch)

1. `registry/unmapped-dgeg.md` row 11 aside ("registry unit string `tep/M€2021` lacks the
   apostrophe the publisher prints") — asymmetry backwards. My own workbook read:
   sheet1 C28 (row 28) resolves to shared string `tep/M€2021` — the publisher itself omits the
   apostrophe on that exact row (C29/C38/C39 use `tep/M€'2021`); the registry is byte-faithful
   to the publisher's inconsistency. Independently re-confirms the spec review's known minor.
2. `registry/core.yaml` scoped comment, last line: "No DGEG data has been ingested" can be
   misread as denying the pre-existing legacy DGEG rows (Task 8 legacy import; the matrix
   itself cites legacy values on rows 8/14, and the synthetic test withholds legacy dgeg
   rows). Suggested wording: "the rebuild pipeline has fetched/parsed/quarantined no DGEG
   data; pre-existing legacy-import rows keyed to these series stay licence-withheld." The
   authoritative doc (`registry/unverifiable.md`) already scopes this correctly
   ("nothing was fetched, parsed or quarantined"), so this is precision only, not a
   factual error in the disposition's mechanics.
