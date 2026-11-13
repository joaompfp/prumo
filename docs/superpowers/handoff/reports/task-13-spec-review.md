# Task 13 — independent specification review (offline, bounded)

Reviewer: independent spec-review subagent. Date: 2026-11-11. Worktree
`/home/joao/projects/prumo-pipeline`, branch `pipeline-rebuild`, reviewed diff
`dcec55d..27bec72` (registry `0a4458f`, code+tests+fixtures `173638c`, report `27bec72`).
**Fully offline: zero HTTP calls made by this review.** Basis: brief + implementer report read
in full; both adapter modules read line-by-line; registry probed programmatically against
`dcec55d` base; 24 hand-built adversarial probes run against the real source/verifier
functions; the 73-test targeted slice executed locally (no live tests).

## Verdict: PASS_CODE / LIVE BLOCKED — Task 13 CANNOT close

Implementation compliance with every offline-checkable brief requirement: **PASS**. The
mandatory live full-scope gate (`test_live_worldbank.py` contract: 930 series, `verified`)
remains **BLOCKED by the publisher-side per-indicator CSV-export outage** documented in the
implementer report (consistent with the 2026-11-11 channel lesson: partial multi-hour outage,
JSON channel healthy, verifier correctly fails closed). The child's 516-series healthy-subset
verification is genuine evidence of correctness but is **not** whole-task completion; nothing
in this review rubber-stamps task closure. Network/outage investigation is the controller's
thread; closing/retrying awaits that.

## What was verified against the brief (with repro)

1. **Diff scope clean** (`git diff --name-status dcec55d..HEAD`): only
   `ingest/sources/worldbank.py`, `ingest/verifiers/worldbank.py`, 8 test/helper files,
   `tests/ingest/fixtures/worldbank/**` (29 files), `registry/{core.yaml,core.proposed.yaml,
   unmapped-worldbank.md}`, the task report. No handoff/ledger/HANDOFF/CLI/legacy-collector
   edits. No commits made by this review.
2. **Registry dispositions** (programmatic probe vs `dcec55d` base): 982 worldbank series
   (unchanged count), 930 active / 52 inactive; **all 52 inactive are `gdp_per_capita_ppp`**
   (none other), their units byte-identical to base (no reinterpretation); every series has
   `native_code` matching `^<indicator>:[A-Z]{3}$`, **unique among active**; 19 indicators
   total / **18 active**; 54 geographies, all `[A-Z]{2}`; EU→EUU, GR→GRC, PT→PRT, AT→AUT
   confirmed by native_code suffix; the 22 previously-missing codes filled, including
   `worldbank.unemployment_wb.AT`; `url` = `https://api.worldbank.org/v2/country/<ISO3>/indicator/<CODE>`
   on all checked actives (0 bad); `unemployment_wb` keeps `unemployment_rate.<geo>.A` keys;
   source block (core.yaml:72-81) holds `licence: CC BY 4.0`, `redistribution_ok: true`,
   `verifiable: true`, attribution 'Source: World Bank'; **core.proposed.yaml worldbank
   section byte-equal to core.yaml, non-worldbank content identical to base** (mirror-only);
   `unmapped-worldbank.md` lists PPP series individually (54 id mentions incl. header refs).
3. **Evidence integrity**: fixture MANIFEST sha256 pins verify 29/29 recomputed here;
   country-metadata.json and meta-NY.GDP.PCAP.PP.CD.json are byte-identical to the controller
   pins (`c9acf393…44bce`, `a95c4834…a1a8d`); `r4-indicator-csv.zip` (142,909 B) is the
   genuine full 3-member archive with the 297,580-byte main CSV (no truncation); all fixtures
   ≤ 200 KB (largest 142.9 KB).
4. **Source adapter adversarial probes** (all behaved as specced — verbatim tokens as plain
   `str`; exponent `1e+22` preserved; `null`→`None` never zero; quoted-numeric, duplicate JSON
   key, non-empty unit, iso3/native mismatch, truncated page count, total=0-with-rows, HTML,
   API error shape, numeric identity label, non-2xx, unrequested-URL-indicator, duplicate page
   all **raise**; `response_index` = [0,1] across a 2-page set; partial page-1-of-2 replay
   parses per the declared fetch-completeness split).
5. **Verifier adversarial probes** (values verbatim incl. tampered `9.9` surfacing for
   verify; empty cell → `observed_text=None`; `observed_unit/flag=None` honest; **one ZIP
   fetch per indicator per check** (3 items → 1 GET); evidence envelope recovers exact ZIP
   bytes + final URL + actual status; extra 4th member, path-traversal `../`, subdir member,
   duplicate year header, wrong indicator code, indicator-name disagreement, HTML-200,
   HTTP 400, garbage body all **raise**). Module imports only stdlib + `ingest.http` +
   `ingest.verifiers` — no collector/collector-parser/flag imports.
6. **Required test matrix present and passing**: targeted run
   `69/…/test_source_worldbank.py test_verifier_worldbank.py test_registry_worldbank_units.py`
   → **73 passed in 17.32s** (matches child's 39+25+9 and controller's 909-total delta +
   deselected live 5). Ruff clean on all touched Python. Registration allowlist test,
   same-process registration test, subprocess guard
   (`worldbank_verifier_entry.py`), ≥5 cross-channel pins incl. 5 PT-GDP intake pins, tamper
   through `verify_run` (value + geography), clean-run-through-`verify_run`,
   `run_with_refetch` registration, offline evidence recovery + `replay_item` — all present.
7. **Politeness/transport**: `ingest/http.py` defaults `throttle_rps=1.0` with min-interval
   sleep, bounded timeout 30 s, UA `prumo-ingest/1.0 (+https://cae.joao.date)` — matches the
   ≤1 req/s documented-UA bounded-timeout requirement; verifier correctly delegates throttling
   to the injected Http.

## Findings

- **No Critical or Important implementation gaps** against the brief in the reviewed scope.
- **Minor (doc only, no edit per controller instruction)**: `ingest/sources/worldbank.py:7`
  docstring says "active coverage = 930 series over **19 indicators** x 54 geographies". The
  930 active series span **18** indicator codes (19th, NY.GDP.PCAP.PP.CD, is inactive); "19"
  is correct only for the all-series registry view and the 19-endpoint metadata sweep cited
  at core.yaml:74. Cosmetic; no code behavior affected.
- **Observation (non-blocking debt for a future ruling, not a defect)**: the verifier evidence
  envelope embeds the full deciding ZIP (base64) **per sampled item**, so a full 930-item
  sample over 18 indicators writes ~930 copies of ~190 KB (~175 MB) though only 18 distinct
  responses exist. Compliant with the versioned-envelope ruling and offline recovery is
  tested, but a content-digest dedup would cut storage ~50×. Do not change unreviewed.

## Explicitly retained failed gate

- Full all-active live verification: **failed-verification, served=0** (CSV export HTTP 400
  after ~150 s / read timeouts on 8 of 18 indicators, per-indicator outage map in the
  implementer report). Fail-closed behavior is exactly per the channel lesson; no series
  inactivated for an outage; no channel switch attempted unreviewed. Healthy-subset run
  (516 series): `verified`, served 25,853 under CC BY 4.0, 516/516 evidence envelopes
  recovered offline — evidence of correctness, **not** task completion.
- Task 13 status stays **BLOCKED on the live gate** pending controller's network-thread
  outcome (retry when the publisher export recovers, or a reviewed alternate decision).
