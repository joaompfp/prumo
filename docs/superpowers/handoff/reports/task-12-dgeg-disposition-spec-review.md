# Task 12B DGEG disposition — independent SPEC review (PASS)

Date: 2026-11-11 · Reviewer: fresh independent spec reviewer · Scope: `869ba6d..fd54d98`, DGEG
safe disposition ONLY (not adapter/ingestion — still blocked) · Method: read-only diff/doc/test
inspection + independent re-derivation of workbook claims from committed bytes. No edits, no
commits, no network.

## Verdict

**PASS.** The disposition is truthful about its blocked status, preserves all 17 original
definitions byte-exactly, and every quantitative claim spot-checked (units, coordinates, tokens,
channel match-rates) re-derives from the pinned evidence. One minor non-blocking annotation
inaccuracy noted at the end.

## What was verified (actual checks run)

**Registry (17 series, no other source touched, identities preserved)**
- `git diff 869ba6d..fd54d98 registry/core.yaml` = **+25 / −0** lines; `core.proposed.yaml`
  byte-identical diff (only header paths differ). 17 `active: false` additions + 8-line scoped
  `verifiable: false` comment block on `sources.dgeg`. Zero deletions, zero edits → ids, units,
  `Mton CO2e`/ktep/TWh/%/tep units, roles, indicator_keys, frequency, geography, `native_code`,
  licence wording all preserved. No ERSE added; one-primary invariant enforced by `load_registry`
  (green load in tests).
- The `verifiable: false` comment is explicitly SCOPED ("current core definitions… NOT a claim
  that DGEG data can never be verified") — matches the brief's ban on an absolute no-channel claim.

**Tests (`test_registry_dgeg_disposition.py`, 6 tests + `test_registry.py`, 23 tests)**
- Ran: `.venv-ci/bin/python -m pytest tests/ingest/test_registry_dgeg_disposition.py
  tests/ingest/test_registry.py -q` → **29 passed in 17.82 s**.
- Refuse-before-network is genuinely asserted: exploding standalone dgeg-labelled doubles (fetch/
  parse/check raise AssertionError if ever called) + empty-script `FakeHttp` +
  `pytest.raises(SourceNotVerifiable, match="verifiable: false")` + `http.calls == []` + zero
  `dataset_run`/`raw_fetch` rows. Not an empty or network-touching test.
- Fetched+legacy withholding test is clearly labelled synthetic (no source/verifier/live claim)
  and proves rows are withheld not deleted (2 observations persist, served stays 0 even with
  `legacy_served='1'`).
- Existing-test edit in `test_registry.py` (`flagged == {"dgeg"}`) is a **strengthening**, not a
  weakening: the old blanket "nothing unverifiable" assertion was stale; the new one pins exactly
  `{dgeg}` and still requires every other source verifiable.

**Evidence bundle (re-derived from bytes, not report claims)**
- Workbook sha256 `5f31904a…837be`, 119,336 bytes — recomputed, matches. All 7 manifest files
  exist, ≤200 KB (max 130,573 B = dadosgov JSON; no 2–13 MB PDFs). Raw vs derived kinds recorded;
  both derived files open with a `DERIVED EVIDENCE — NOT the raw HTTP response…` header naming
  source-PDF URL/sha256/bytes and pdftotext method (APN d4490a8e…07a7 / 2.4 MB, AEN 9486137e…c4db1
  / 13 MB). No fake raw evidence.
- Workbook raw-XML spot re-derivation (this review read `xl/worksheets/sheetN.xml` cells
  directly):
  - s1 r10 dependence 2024p token `0.64312837828385205`, style → numFmt `0.0%` → fraction-under-
    percent-format claim TRUE; tokens never relabelled percent-scale anywhere in the matrix.
  - s1 r20 electricity `TWh(1)` 2024p `51.357999999999997`; s2 r21 ktep 2024p `4349` ✓.
  - s1 r22/r24 co2 `Emissões Totais(2)` / sector rows, unit `Mton CO2e`, 2024p = `nd` ✓.
  - s1 r13 (`% produção doméstica…CEP`, 2024p `0.39405298811534401`) = the legacy
    `primary_energy_consumption` misassignment row ✓.
  - s2 r17 final energy ktep 2024p `16713`; s1 r18 unrounded counterpart exists per matrix ✓.
  - s3 r13 FER-T 2004 token `4.0000000000000001E-3` (scientific notation) ✓; FER-E/FER-Global/FER-T
    row coordinates r12/r11/r13 ✓.
- APN derived-text re-comparison against workbook 2015–2024 columns (Y..AH), independent of the
  report: CEP — workbook vs APN `…20 814 | 20 822 vs 20 812 | 21 315 vs 21 313 | 20 646 | 20 346`
  → exactly **8/10 with drift only at 2021/2022** ✓; electricity ktep **10/10 token-exact** ✓;
  final energy ktep **10/10 token-exact** ✓; dependence display-exact **10/10** at 0.1 % ✓. The
  matrix's central claims (blocked-but-real-partial-channels) hold byte-exactly.
- Intensity rows s1 r28/29/38/39 confirmed base-2021 units; registry strings match the publisher
  exactly (see minor note).

**Docs and licence wording**
- `unmapped-dgeg.md`: 17-row matrix, one row per registry id, each with workbook coordinate,
  native unit, reason category, honest partial-channel finding and per-row resumption criteria;
  distinguishes unit conflict / duplicate / misassignment / base-year / vintage / representation /
  weak-independence; explicitly rejects "no channel" and the fraction→percent relabelling.
- `unverifiable.md`: stale "adapter exists / data still collected / nothing unverifiable" wording
  correctly replaced; REN reclassified verifiable-but-licence-withheld (≠ unverifiable);
  INE verified. Accurate.
- `licences-todo.md`: old ungrounded dadosgov claim replaced with evidence-cited wording
  (terms shell, All-Rights-Reserved footer, AEN "Todos os direitos reservados", LADA statute ≠
  grant, dadosgov CC BY = 19 geology datasets only). Stays at "unconfirmed grant", explicitly NOT
  a categorical illegality determination. `redistribution_ok: false` and old
  "UNVERIFIED — builder must confirm before serving" pin are grounded.
- Scope discipline: changed-file list = registry (3) + tests (2) + docs (2) + evidence (8) +
  implementer report only. **Migrations 001–005 untouched; no ingest/adapter/verifier/model code
  changed; no HANDOFF/ledger/controller files in the diff.**

## Minor non-blocking note (no action required for this gate)

`registry/unmapped-dgeg.md` row #11's aside — "registry unit string `tep/M€2021` lacks the
apostrophe the publisher prints" — has the asymmetry backwards: the publisher workbook cell
s1 C28 itself prints `tep/M€2021` (apostrophes appear only on C29/C38/C39 as `tep/M€'2021`), so the
registry is byte-faithful to the publisher's own inconsistency on that row. Harmless annotation
drift in a parenthetical; the disposition (preserve string exactly) is correct. Controller may
fix the aside next registry touch; not a blocker.

## Blocking findings

None.
