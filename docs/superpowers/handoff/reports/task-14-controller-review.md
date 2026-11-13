# Task 14 - FRED controller acceptance

Task 14 is technically COMPLETE through implementation commit `6e867c7`, after independent specification and quality reviews and scoped fix re-reviews. Serving remains WITHHELD: the IMF redistribution permission is unconfirmed and `source.redistribution_ok=false`. This is not a deployment or permission grant. Task 13 World Bank remains OPEN on its separate fresh-network export gate; the owner explicitly authorized advancing Task 14 with that blocker recorded. Task 15 has not started.

## Scope and delivered contracts

`FredSource` fetches the keyed FRED JSON API, preserving JSON-string value tokens, metadata responses and observation response indices. Only explicit `api_key=` or `FRED_API_KEY` is supported in production code. The controller supplied the existing legacy key for acceptance without printing it, putting it in process arguments or persisting it on f0nix. Archived URLs and params explicitly omit the query credential; original publisher body bytes are unchanged. Credential echoes are refused before archival and request failures are sanitized.

`FredVerifier` independently reads the keyless, server-rendered `/data/<CODE>` HTML table. Its own structural parser reads both actual units and full-precision values from one response. It imports no collector/parser helper, passes normal registration and the subprocess independence guard, and receives blind items. The proposed `fredgraph.csv` channel was rejected after original exports exposed exact-Decimal differences on 10 of the 12 IMF series. No precision tolerance, rounding or unit conversion was introduced. The rounded series landing page is not the verification channel.

The registry has 12 active, unique IMF global commodity series, with exact publisher unit labels, monthly frequency, NSA, native codes and canonical URLs. Five proven `commodity_*` primaries received missing codes without role changes. Eight entries are inactive with original definitions preserved: five coded same-source twins, the steel subset duplicate, the US BLS index misidentified as a global USD steel price, and US Henry Hub misidentified as a global benchmark. `registry/unmapped-fred.md` lists every disposition. The scaled legacy cotton orphan remains unmapped. `core.proposed.yaml` mirrors the same scoped FRED changes because existing repository tests pin equality with `core.yaml`.

## Independent review gates

The initial specification review passed. Independent quality review required corrections for silent partial-archive replay, noncanonical Unicode dates and a restriction-parameter identity hole. Round 1 introduced one page ledger for stable count/limit/realtime/extent/offsets, full archive completeness and ASCII Gregorian dates. The quality re-review then found the remaining params-side strict-superset operator: round 2 changed it to an actual subset assertion and added genuine-first-page and self-consistent restricted-window regressions.

Final gate reports:

- `task-14-spec-review.md`: initial PASS.
- `task-14-quality-review.md`: initial REQUEST_CHANGES, findings retained as history.
- `task-14-fix-1-spec-review.md`: PASS.
- `task-14-fix-1-quality-review.md`: REQUEST_CHANGES for the remaining params guard.
- `task-14-fix-2-spec-review.md`: PASS.
- `task-14-fix-2-quality-review.md`: APPROVED, no remaining Critical or Important findings.

The controller independently reran all 24 negative probes after the final fix: zero failures, including complete valid archive and paginated positive controls, truncated/tail/count/extent drift, unknown URL and params keys, duplicate query keys, Unicode aliases and invalid Gregorian dates. The documented minor about an absent interior HTML row remains: a sampled missing period fails verification, while unsampled evidence absence is a sampling limitation. No new verifier semantics were added to conceal that limitation.

## Fresh live acceptance, final code

The actual registered verifier and `run_with_refetch` ran on all 12 active registry series, in an isolated scratch database, with every real HTTP request routed through the planned production egress on f0nix. This was a fresh network run, not fixture HTTP or replay promoted into a live claim. The HTTP bridge was bounded to 48 requests, a 180-second network phase, a 12-second remote request timeout, zero implicit retries and one whole-dataset attempt. Credentials travelled only over SSH stdin.

Final run started 2026-11-12 13:59 UTC, implementation `6e867c7`:

| Measure | Actual result |
|---|---|
| Active series covered | 12 of 12, no omissions or duplicate native codes |
| Real origin responses | 36 of 36 HTTP 200: 12 metadata, 12 observations, 12 independent HTML tables |
| Final state | verified |
| Written observations | 5,004, 417 per series, 1992-01 through 2026-09 |
| Quarantine | 1,728 non_numeric cells, the publisher's 144 pre-1992 '.' cells per series |
| Sample | 120 of 120 exact Decimal matches, including latest per series and random history |
| Served | 0, enforced by the real redistribution_ok=false licence gate |
| Raw collector records | 24, retaining metadata and observation bytes |
| Archived independent evidence | 12 distinct status-bearing HTML envelopes |
| Offline audit | all 120 comparisons recovered and checked against archived values and actual units, without HTTP |
| Elapsed | 39.45 seconds |

The controller also exercised the committed live pytest with the real RequestsHttp client and environment credential: `tests/ingest/test_live_fred.py -m live -s` -> 1 passed in 53.10 seconds. It independently reproduced verified / 5,004 written / 1,728 quarantined / 120 matches / 0 served, and offline evidence replay. The live test now derives expected coverage and missing-cell counts from that run's archived publisher responses instead of freezing fixture dates or monthly counts. Its timeout is explicitly per request, with retries=0 and max_attempts=1; it does not claim a whole-phase deadline.

## Regression and legacy safety

Controller final full suite: `.venv-ci/bin/python -m pytest tests -q` -> 1,026 passed, 6 live deselected, 1 warning, 226.61 seconds. Ruff passed on all FRED source, verifier and test helper paths. No core, HTTP, importer or SQL behavior was changed.

A fresh full legacy CSV import against the current registry was separately exercised in an isolated database. Actual result: 161,263 imported; quarantine 7,468 missing_unit, 6 non_numeric, 480 suspect_unit_scale and 3,082 unit_mismatch; 73,863 not_in_registry; 0 served. FRED alone: 3,779 missing_unit, 3,082 unit_mismatch and 3,007 retained legacy-unverified rows. A second import wrote zero new observations or quarantines (only the 73,863 not-in-registry report count recurred). Old bare-USD values for corrected active FRED definitions were rejected, never relabelled or converted. Historical Task 8/10 counts in earlier reports describe their earlier registry and are superseded by this current-registry result for present acceptance.

## Durable evidence

`docs/superpowers/handoff/evidence/task-14-fred/live-acceptance-capsule.tar.gz` is a controller-created audit capsule, NOT an original publisher archive. It contains the isolated SQLite database, the exact raw-store payloads and HTML envelopes, all 36 original network response bodies, request provenance and the controller acceptance script. API-key values are omitted from public URL/params records; no publisher body was rewritten.

Final capsule: 657,110 bytes, SHA256 `4bf0e5114c8ac714df706ecbae26fbcbea13522e233ed785eb229f39c70e4e7b`, 76 regular-file members. It was reopened, path/member types and every member hash checked, the 36 original response statuses and hashes checked, and all persisted bytes swept for the credential. `live-capsule-manifest.json`, `live-report.json` and `live-request-manifest.json` sit alongside it. The capsule records its original scratch root for relocating absolute database raw paths during offline inspection; scratch retention is not required to preserve the evidence.

The original fixture manifest pins 48 unchanged publisher responses, each at most 93,921 bytes. Terms and concept-conflict originals remain in the same evidence directory.

## Remaining project gates

Task 17 must register FredVerifier, supply the explicit key contract, ignore inactive series and expose legal withholding separately from failed technical verification. Task 18 must provision the FRED key securely for the deployed ingestion service; the local legacy key's existence is not production configuration. IMF redistribution consent is not established. The owner must resolve that before any serving eligibility change; no outbound request for permission was sent.

Task 13 remains OPEN on its documented CSV timeouts/502; no additional World Bank retry loop was run here. DGEG ingestion remains blocked. Task 15 OECD is the next unstarted adapter. No merge to main, scheduler change, ingestion deployment or public UI change was made.
