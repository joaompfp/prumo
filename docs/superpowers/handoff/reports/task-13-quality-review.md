# Task 13 — independent quality review (offline, bounded)

Reviewer: independent quality-review subagent. Date: 2026-11-11. Worktree
`/home/joao/projects/prumo-pipeline`, branch `pipeline-rebuild`, scope `dcec55d..27bec72`.
Basis: brief + implementer report + spec review; both adapter modules read line-by-line; all
five Task-13 test/helper files read line-by-line; 24+ registry/manifest claims recomputed
programmatically from live git objects and fixture bytes; the 73-test slice executed locally;
~26 novel hand-built adversarial probes run against the real source/verifier code
(`~/.hermes/cache/scratch/wb_adversarial*.py`). **Zero HTTP calls by this review** — the live
gate evidence is taken from the implementer report, not re-probed.

## Verdict: APPROVED_IMPLEMENTATION / LIVE BLOCKED — Task 13 CANNOT close

No Critical, no Important findings. Code quality is high: the fail-closed contract is
comprehensive, honest, and independently re-verified below. The mandatory live full-scope gate
(930 series, `verified`, all 18 active indicators) remains **blocked by the publisher-side CSV
export outage** committed in the implementer report (per-indicator outage map; NE.EXP.GNFS.ZS
HTTP 400 after ~150 s, read timeouts on 8/18 indicators) — consistent with the 2026-11-11
channel lesson. The 516-series healthy-subset verification (verified, served 25,853, 516/516
evidence envelopes recovered offline) is genuine correctness evidence, not task closure. No
all-sources LIVE PASS is claimed anywhere it isn't earned.

## Independently re-verified claims (reproduced offline)

- **Test slice**: 73 collected, **73 passed in 17.89 s** (my run, `.venv-ci`,
  no live marker); ruff clean on all 8 touched Python files.
- **Diff scope** (`git diff --name-status dcec55d..27bec72`): source, verifier, 8 test/helper
  files, 29 fixture files + MANIFEST, 3 registry files, implementer report. Nothing else.
- **Fixture evidence integrity**: MANIFEST carries **29 entries**; all 29 sha256 pins + byte
  sizes recomputed here = 0 mismatches; manifest ↔ disk sets identical; all ≤ 200 KB, all
  status 200. Controller pins byte-exact: `country-metadata.json` =
  `c9acf3932785191a649cbc04c3056af4cf64a236e5c3b49d49be25ddb0440bce`,
  `meta-NY.GDP.PCAP.PP.CD.json` = `a95c4834552a80e2c6b755c22e887d401d7930c2b97453f76fc063108a4a1a8d`
  (matches the constant pinned inside the test suite). All three CSV ZIPs are genuine
  3-member archives (main CSVs 297,580 / 196,626 / 141,894 bytes uncompressed).
- **Registry probes** (parsed `core.yaml`, diffed against `dcec55d` base via pyyaml on git
  objects): 982 worldbank series / 930 active / 52 inactive; inactive set is exactly
  `gdp_per_capita_ppp` (indicator `NY.GDP.PCAP.PP.CD`, units `USD (2017 PPC)`/`USD (2017)`
  preserved unedited); 19 indicators total / **18 active**; 54 geographies all `[A-Z]{2}`;
  native_code `^<indicator>:<ISO3>$` on 982/982; 930 active native codes unique; `url`
  canonical on 930/930 active; EUU/GRC/AUT/PRT mapping spot-checked. Preserved-field drift vs
  base = **0** across unit/role/indicator_key/theme/geography/frequency/decimal/id/source;
  the only row-level change is +{native_code (22 previously blank), url, active}. Source block
  base→current change is exactly `verifiable: True` added (licence CC BY 4.0,
  redistribution_ok, attribution were already present). **Non-worldbank rows changed: 0**
  (DGEG/REN and all other sources untouched). `core.proposed.yaml` worldbank section equals
  core.yaml worldbank rows; its non-worldbank content equals base. `unmapped-worldbank.md`
  lists exactly the 52 inactivated ids and carries the pinned PPP metadata hash. All 19
  archived indicator-metadata names/sourceNotes back the registry unit-alias table (e.g. "%
  of GDP", "crude (per 1,000 people)", "years", "Gini index", "current US$", and the PPP
  conflict "current international $" + "current prices", `unit: ""` on all).
- **Independence**: verifier imports only stdlib + `ingest.http` + `ingest.verifiers`; the
  native-code split is deliberately duplicated; registration allowlist, same-process test and
  the `assert_verifier_independent` subprocess guard (blocked prefixes
  `collectors`/`ingest.flags`/`ingest.sources`) are all present and exercised in the suite.

## Novel adversarial probes (beyond the committed tests and spec review)

Source module (all pass — raise `ValueError`, fail closed):
`page=1.5`, `page=true`, `total="19x8"`, list-shaped row element, `value=true`, extra row key,
`decimal=1.5`, duplicate key inside a row object, empty `indicator.value` label — all raise.
Token fidelity: JSON `1e+22` preserved as `"1e+22"`, a 25-digit integer token preserved
digit-exact, both surfacing as plain `str` into RawRow (quoted-numeric injection remains
impossible; covered by committed test too).

Verifier module (fixture-derived mutant ZIPs through the real `check()`):
- Raise, as designed: lying central-directory file_size (patched +16), missing member (2/3),
  subdir member name, absolute-path member name, duplicate metadata member name, notes-style
  trailing row with non-ISO3 field, trailing blank line, trailing junk bytes after final CSV
  newline, non-ascending year header, non-digit year label, UTF-16-encoded main CSV, year-hole
  (removed "2019" column: 2020 still served; requesting 2019 raises "no column").
- Value identity on an unquoted numeric cell is unchanged (`'346639825141.821'` verbatim).
- Evidence envelope is deterministic across calls; an actual wire status of 201 is recorded
  verbatim (and accepted, correctly, as 2xx).
- Corrupt compressed-stream bytes raise — but as **`zlib.error`, not the module's
  `ValueError`** (see Findings, O2).
- Two accepted mutants examined and shown **inert** (O3, O4).

## Findings

**Critical: none. Important: none.**

Minor (documentation only — no edits per controller instruction):
- M1. `docs/superpowers/handoff/reports/task-13-report.md:59` and `:202` state "28 fixture
  files"; the committed set is **29** files (MANIFEST.json lists 29 and pins 29; on-disk
  non-MANIFEST count = 29). Off-by-one in the implementer narrative; the evidence itself is
  complete and correctly pinned.
- M2. `ingest/sources/worldbank.py:7` docstring: "930 series over 19 indicators" — 930 active
  series span **18** indicator codes (19th is the inactivated PPP indicator). Already noted by
  the spec review; confirmed here. Cosmetic.

Observations (fail-closed behavior holds in every case; none is a blocker; do not change
unreviewed):
- O1. Per-item evidence envelopes embed the full deciding ZIP (base64) per sampled item —
  ~175 MB at full 930-item scope over 18 distinct responses. Content-addressed raw store
  dedups identical bytes (`test_archived_evidence_recovers_offline_and_replays` sees 2 payload
  paths for 2 indicators), so DB-side storage is the cost. Spec review already flagged this;
  concur: compliant, recovery tested, dedup would be a storage win.
- O2. Decompress-time corruption inside a member raises bare `zlib.error`
  (`ingest/verifiers/worldbank.py:99-105` `_read_member` wraps only the size contract;
  `zipfile.BadZipFile` mapping at `:115-117` covers open/structure only). Fail-closed is
  preserved (no false pass is possible), but the module's otherwise uniform `ValueError`
  failure vocabulary has this one leak — a harness catching only `ValueError` per item would
  see a hard crash instead of a clean item failure. Same class: truncated mid-member reads
  (`EOFError`). One-line hardening (wrap the read in ValueError) is a reviewable follow-up.
- O3. `zipfile` tolerates arbitrary trailing bytes after a valid archive (probe V1: accepted).
  The compared bytes remain CRC- and length-checked member contents only, and the exact full
  body (junk included) is archived in the evidence envelope; trailing dead bytes cannot
  influence any compared value. A smuggled second archive would read as archive substitution —
  within the capability of a fully hostile channel anyway. Strict EOF-at-EOCD validation would
  harden robustness; not a correctness hole.
- O4. A shape-valid phantom country row (unknown ISO3 like `ZZZ`, matching indicator
  name/code) is accepted (probe V7b) but is inert: verifier items derive iso3 from registry
  `native_code`, so such rows are never consulted for any real series, and a duplicated real
  country code raises. Restricting rows to the publisher country set would couple the verifier
  to collector-side evidence and break the blindness protocol — the current tradeoff is
  correct.
- O5. Metadata members are name/count-validated but never read; their declared sizes feed the
  total cap, but no realized==declared check applies to them. Safe as designed (their content
  never participates in a comparison), stated here so the boundary is explicit.

## Explicitly retained failed gate

- Full all-active live gate: **BLOCKED — unresolved publisher network condition** (CSV export
  partial outage, 8/18 indicators HTTP 400 after ~150 s / read timeouts, JSON channel healthy;
  verifier failed closed, served=0, no series inactivated for the outage, no channel switch).
  The controller's bounded probes (12 s timeouts, 3 variants, GDP200-vs-NEEXP contrast) remain
  the open network thread. Healthy-subset 516-series evidence is genuine but does not close
  the task. No LIVE PASS is asserted here.
