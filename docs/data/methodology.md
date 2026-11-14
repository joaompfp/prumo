# Base-data methodology

This document describes the implemented `ingest/` pipeline, not the retired dashboard.
SQLite is the system of record. The deployed HTTP app remains in maintenance mode and
does not expose the data store as a public data API. [Operations](operations.md) owns
runtime procedures and the open observation gate; the [handoff](../superpowers/handoff/HANDOFF.md)
and its decision ledger own acceptance and later rulings.

Terminology: HTTP is Hypertext Transfer Protocol; JSON is JavaScript Object Notation;
CSV is comma-separated values; SQL is Structured Query Language; UTC is Coordinated
Universal Time. INE is Portugal's Instituto Nacional de Estatística; BPstat is Banco
de Portugal's statistical service. Other publisher names and exact source identifiers
are recorded in the [source catalogue](sources.md).

## Registry and scope

[registry/core.yaml](../../registry/core.yaml) is authoritative for source metadata,
series identifiers, indicator keys, primary/cross-check roles, native codes, geography,
frequency, unit, multiplier, adjustment, base year and eligibility. The source catalogue
is generated from it. Inactive definitions are retained and are not scheduled; the
catalogue must not imply that every listed definition is ingested or queryable.

Primary assignments favor the institution closest to the data's origin. A cross-check
role does not authorize substitution for the primary. The schema can record
`cross_check_gap`, but there is no generic implemented cross-source reconciliation or
automatic correction policy. Independent verification below uses a different channel
of the same publisher and is separate from cross-publisher comparisons.

## Raw stage

Each received collector response is archived byte-for-byte under
`<raw-dir>/<source>/<sha256[:2]>/<sha256>`. SHA-256 is the content hash. Identical bodies
can reuse the same file while retaining separate retrieval receipts. `raw_fetch`
records source, the adapter-supplied response URL and request parameters, HTTP
status, actual retrieval time, byte count, hash and path. This table has one URL
field, not separate request/final URL fields; capture manifests retain both.
Credentials must not enter recorded URLs or parameters. Responses received before a later fetch failure
remain evidence; an incomplete fetch is never promoted to queryable fresh data.

Observation provenance uses the response each parsed row actually came from, via
`RawRow.response_index`, rather than assigning every row to the first response. The raw
store holds original bytes, not a reconstructed spreadsheet or reformatted JSON file.
Verification responses are archived separately under `verify-<source>`; envelopes may
retain multiple exact responses plus metadata needed for identity or unit comparisons.

## Validated stage

Source adapters extract publisher numeric tokens as text, without a binary-float
round-trip. The common validator trims surrounding whitespace, normalizes periods,
checks numbers using the registry's declared decimal separator, checks exposed units
and quarantines invalid rows. Reasons include `bad_period`, `non_numeric`,
`unit_mismatch` and `duplicate_period`. Every otherwise-valid duplicate for a period
is quarantined, even when the values agree; no copy is silently chosen.

The pipeline does not interpolate, fill gaps, rescale, round or convert units. Registry
metadata describes the publisher's quantity. If no row-level unit is exposed, the
reviewed registry unit is used; this does not authorize inventing a missing legacy
unit. The legacy importer additionally rejects missing units, known suspect scales
and unit mismatches rather than converting old values.

`value_text` is the precision-preserving publisher token used for audit and exact
comparisons. `value` is also stored as a numeric REAL/float convenience field and is
not an exact decimal representation. For INE the stored token is JSON `valor`;
`ind_string` can preserve additional display trailing zeroes and remains in the raw
response. Exact numeric agreement with an independent channel does not claim
byte-identical display formatting across channels.

Periods retain their native frequency: annual `YYYY`, semiannual `YYYY-S1`/`YYYY-S2`,
quarterly `YYYY-Q1` through `YYYY-Q4`, monthly `YYYY-MM`, daily `YYYY-MM-DD`, and
E-REDES quarter-hour `PT15M` in canonical `YYYY-MM-DDTHH:MM:SS+00:00`. Native E-REDES
UTC stamps are not converted from the publisher's auxiliary Lisbon display clock or
aggregated into daily values.

A series with no valid observations emits a `format_change` event. Other populated
series may continue; if every series is empty the dataset fails validation. A run's
success alone therefore does not prove coverage of every registered series. Review
per-series status, quarantine reasons and events.

## Status flags

The reviewed common vocabulary is `normal`, `revised`, `estimated`, `provisional` and
`break`. When multiple mapped flags occur, precedence is
`break > provisional > estimated > revised > normal`. A `revised` publisher flag and
a locally detected `revision` event are different records.

- `normal`: no mapped status qualification; not a guarantee against all quality caveats.
- `revised`: publisher marks a correction or revision.
- `estimated`: estimated value or another reviewed accuracy/forecast qualification.
- `provisional`: provisional or preliminary publisher status.
- `break`: a break or definition difference affecting comparability.

Unknown publisher flags fail closed rather than becoming `normal`. Mappings compress
publisher vocabulary: Eurostat definition differences map to `break`, and several
accuracy statuses map to `estimated`. The reviewed INE quality sign `§` maps to
`normal`, losing that qualification in the common flag. Raw evidence preserves the
original symbols/descriptions. See [flag mappings](../../ingest/flags.py) and the
individual adapters/verifiers for source-specific policies.

## Independent sampled verification

The normal operational path registers the reviewed verifier and uses
`run_with_refetch`. A missing registered verifier or `verifiable: false` prevents
fetching on that path. The verifier receives series identity, period and specification,
not the expected value or expected status flag. It independently parses a different
publisher endpoint or format; it must not import the collector or share its parser
or flag helpers. Static registration rules and subprocess independence tests enforce
the reviewed boundary, not a general-purpose sandbox against malicious code.

### Sample design (procedure `prumo-sample-v2`, [ingest/sampling.py](../../ingest/sampling.py))

Let N be the number of observations a run wrote and S its number of series. The verifier
compares a sample built in five steps; each item stores the step that drew it
(`verification_item.reason`):

1. `latest`: the latest period of every series (S items, a census of the newest data).
2. `changed`: every observation the run revised (event `revision`) or added to a series
   that already had verified fetched data (event `new_periods`), at most 500 per run. Above
   the cap, 500 are drawn at random and the rest stay in the history pool; the total, the
   number checked and the cap are stored in `verification.sample_design`.
3. `series-stratum`: each series' remaining observations (its history pool) are split by
   period into an older half and a recent half, and one random observation is drawn from
   each non-empty half (up to 2S items; fewer where a series has less history).
4. `random`: a simple random sample, without replacement, of the history pool left after
   step 3, of size n = the smallest n for which a sample from the whole pool of size P
   (all observations not taken by steps 1-2) misses every one of D = ceil(0.01 * P)
   defective observations with probability at most 5%, computed exactly from the
   hypergeometric distribution: prod over i < n of (P - D - i) / (P - i) <= 0.05.
   n grows with P and tends to 298: 258 for P = 1,000, 281 for 2,500, 294 for 10,000.
5. `same-response`: every other observation that the verifier reads from a response it
   already fetches for steps 1-4 (`Verifier.request_key`). Where one response carries a
   series' full history, this costs no extra HTTP request and turns the check into a
   census of that series.

Statistical statement: steps 1, 2 and 5 are censuses of what they cover. Step 4 alone
detects, with probability at least 95%, any error rate of at least 1% among the history
pool. Steps 3 and 5 only add items, and drawing step 4 after removing step 3's items can
only lower the miss probability (each factor 1 - D/(M - i) decreases as the population M
decreases), so the bound holds for the whole design. A single mismatch fails the run, so
"100% of the sample matched" means: no error was found in any compared cell, and an error
rate of 1% or more in the unverified remainder would have been found with at least 95%
probability.

Randomness is reproducible without depending on the Python version: each candidate gets the
rank `sha256("prumo-sample-v2" US seed US stratum US series_id US period)` (US = the 0x1F
separator, lowercase hex) and each step takes the lowest ranks of its stratum. The seed is
63 random bits from `secrets`, stored on `verification.seed`; `draw_sample` redraws the same
sample from the stored seed, the run's observations and events, and the verifier's
`request_key`. Verifications stored before migration 0012 used Python's
`random.Random(seed).sample` with a fixed target of 50 (labelled
`v1-python-random-sample`); their items remain stored, but that draw is not re-implemented.

What this means per source, for the current registry (active groups; observation counts from
the latest production runs):

| Source (groups) | Series per group | Before (fixed 50) | After |
|---|---|---|---|
| Eurostat (1) | 329 | 329 latest cells, no history | every observation (one TSV per dataset key carries the full history) |
| World Bank (18) | ~52 | ~52 latest cells per indicator (949 in all), no history | every observation (one bulk ZIP per indicator; ~45,900 cells) |
| FRED (1) | 12 | 50 | every observation (one table page per series) |
| OECD (1) | 6 | 50 | every observation (one CSV per series, window = the run's span) |
| E-REDES (1) | 3 | 50 of 864 | every observation of each sampled UTC day (all days of a 3-day run) |
| REN (1) | 14 | 50 of 182 | every series of each sampled chart-month (about all 182) |
| INE (1) | 41 | 50 of ~1,400 | ~383 (41 latest + 82 strata + 260 random) + changed cells; one selection request each |
| BPstat (1) | 10 | 50 of ~4,300 | ~318 (10 latest + 20 strata + 288 random) + changed cells; one request each |

INE and BPstat answer one request per item, so their verification now takes several
hundred throttled requests (minutes, at the 1 request/second policy).

### What an item compares, and why a field may not be compared

Every sampled item must match: exact series/period identity, exact `Decimal` numeric
value with no tolerance, and unit/status flag when the independent channel exposes
them. Different trailing zeroes can compare numerically equal. Each item stores the fields
it compared (`verification_item.compared`). When a channel cannot expose the unit or the
flag, the verifier declares why (`Verifier.not_compared`) and the reason is stored on the
item (`unit_not_compared`, `flag_not_compared`); an item without the field and without a
declared reason fails. The declared reasons per source are:

| Source | Unit compared | Flag compared |
|---|---|---|
| Eurostat | no: the TSV shows only the unit code pinned in the requested key | yes |
| World Bank | no: the bulk CSV has no unit column | no: no status surface |
| FRED | yes | no: DATE/VALUE table only |
| OECD | yes | yes |
| E-REDES | yes (metadata labels) | no: no status surface |
| REN | balance rows yes; market chart no unit annotation | no: no status surface |
| INE | yes | yes |
| BPstat | yes | no: no observation status on the portal |

Missing results, wrong result count or order, parsing errors, missing evidence and
mismatches fail verification. A 100% match of the sample is mandatory; where the sample is
not a census it does not prove every unsampled row (the statement above quantifies it).
A separate full-row check against archived collector bytes, when performed, has a different
evidentiary scope and must be reported separately.

### Evidence and replay

Every item must carry the evidence bytes it was decided from (an item without evidence
fails); they are archived under `verify-<source>` and the exact spec the series was verified
with is stored in `verification_spec`. Each verifier implements a pure
`reread(evidence, item)`. `replay_item` loads the archived evidence (integrity-checked
against its SHA-256 name), re-reads it with the verifier's `reread`, requires the result to
equal the stored claim (key, observed text, decimal, unit, flag), and then re-decides the
stored comparison. A missing, corrupt or disagreeing piece of evidence does not replay as a
match. Items stored before migration 0012 need the registry specs passed in.

### Failure, outage and escalation

A failed verification keeps that run out of the served view and triggers a full refetch of
its dataset group with a fresh seed, up to three total attempts by default. A verifier
OUTAGE is different: when the verifier channel answers a non-2xx status or the connection
fails (`VerifierUnavailable`, `OSError`), no item could be compared, so the dataset is not
re-downloaded; the run ends `failed-verification` with event `verifier_outage`. Giving up,
after an outage or after the last failed attempt, writes event `verification_escalated`
(reason, the failed run ids) and the operator report shows the reason. A verifier that
raises on unexpected content (drift) is a genuine failure and is refetched. Fetch/validation
failures return their own failure state; scheduler retries are a separate policy. World
Bank runs are grouped per indicator across all its registered active geographies; other
sources run their active series as one dataset. A failed World Bank indicator does not stop
healthy siblings.

There is an accepted exception to fresh sampling: responses with the same fingerprint
as the immediately previous verified run of the same dataset short-circuit to
`verified`, with no new observations or verification sample. Prior verified rows stay
queryable; no new independent verification date is invented, but the re-fetch does count
as confirming the retained data current for staleness (see the status definition below).
Identical bytes after a failed run are fully processed again.

The per-source collector and reviewed independent channel are documented in
[sources.md](sources.md), including blocked definitions and unknown channels. Technical
verification does not resolve redistribution rights.

## Served stage and vintages

`served_observation` is the SQL eligibility boundary. It requires a verified run and
`source.redistribution_ok=1`, including for legacy rows. Licence revocation withdraws
rows from this view without deleting stored history. FRED, OECD and REN can be
technically verified while remaining withheld. DGEG's current definitions are inactive
and marked not verifiable; no new DGEG adapter or ingestion is implied. See
[licence decisions](../../registry/licences-todo.md) and
[unverifiable definitions](../../registry/unverifiable.md).

For each series/period, verified fetched data wins over eligible legacy data. Among
fetched rows the vintage with the latest retrieval time (`observation.fetched_at`, the
original receipt time for recorded replays) wins, ties broken by the greater observation
id; legacy rows keep the greatest-id rule (they are imported in retrieval order). This is
our retrieval time, not a publisher revision timestamp. Fetched rows of an inactive series
are not served, and a run withdrawn through the reviewed `withdraw` command is never
served (see [operations](operations.md)). New vintages append observations; failures do
not overwrite last-good rows. The observation table retains earlier vintages even when
only the selected current vintage is queryable through the served view.

Revision events compare new `value_text` with the currently served verified fetched
value; formatting-token changes can therefore emit revisions. This is not a complete
publisher revision log: legacy comparisons are excluded and withheld-source changes
may not emit events because the prior value is hidden by the licence-gated view.

Legacy imports retain `kind=legacy-unverified`, their original retrieval dates and no
raw payload, even though the synthetic import run is internally marked `verified`.
That state is not independent verification. The global legacy switch stays disabled;
the reviewed scoped switch permits only active, licensed World Bank legacy continuity.
Fresh eligible data supersedes it for the same period. Other sources are not granted
legacy continuity by that decision.

## Dates, catch-up and recorded input

The reference `period` states what was measured. `fetched_at` records actual retrieval;
`released_at` is a distinct optional publisher release field, not a date inferred from
the period. `started_at`/`finished_at` describe processing attempts; verification has
its own timestamp. Initial catch-up records when it actually runs, never an invented
April ingestion date. Re-fetching missing months obtains the publisher's current
vintage. Revisions that occurred during the April-to-November 2026 collection gap
cannot be reconstructed; pipeline vintage history begins with actual ingestion.

`replay --from YYYY-MM` performs a fresh re-fetch. Its cutoff scopes only E-REDES'
explicit day window; other sources fetch their native histories. It is not an offline
rebuild command. The `replay_item` Python helper re-reads each item's archived evidence with
the verifier's pure `reread` and re-decides the comparison without network (see Evidence and
replay above).

Original-file imports use validated `capture` bundles for World Bank/E-REDES only.
All attempts are marked `input_origin=recorded`; original collector receipt times
remain the data's `fetched_at`, while processing time stays current. The collector reads
only the bundle, but the verifier reads the publisher over live HTTP: a bundle that was
edited consistently (collector and verifier responses together) cannot verify itself, and
an offline replay fails verification with a clear `verifier_outage` escalation. Recorded
input gets one attempt (re-reading the same bundle is not a refetch). Only the explicit
`run --bundle DIR --pinned-verifier` flag verifies against the bundle's own captured
verifier responses; that is NOT audit-grade evidence and is stored on every such
verification as `verifier_channel='pinned-bundle'` (recorded runs verified before migration
0012 are labelled that way too, because that is how they were verified). Older recorded
data cannot replace newer verified group data: per-group preflight and an atomic
write guard enforce that rule. Receipts more than five minutes in the future are
rejected. A byte-identical bundle may use the verified-payload short-circuit rather
than draw another sample. Browser files without real HTTP receipts remain unaccepted
originals, not importable bundles with invented dates/statuses.

Follow [manual refresh](manual-refresh.md) for capture rules and the linked
[stop/import/restart runbook](operations.md#manual-update-with-original-response-bundles)
for f0nix writes. The scheduler lock coordinates scheduler instances only. Interrupting
production continuity requires a new observation window, not an assertion that the
original 24-hour gate passed.

Status staleness uses the implemented refresh policy (registry `schedule`, else the
frequency default A/S=30d, Q=7d, M/D/PT15M=1d). It is not proof of the publisher's
latest possible release. `status` reports two retrieval dates per series:

- `real_data_fetched_at`: the latest `fetched_at` of the retained observations, i.e. when
  the bytes now held were received from the publisher.
- `last_confirmed_current`: the latest publisher retrieval of a run that is still
  `verified` and either wrote that series' observations, or is an identical-payload
  short-circuit whose matched run (followed through earlier short-circuits) is still
  `verified` and holds that series. An unchanged publisher file that the scheduler
  re-fetched and found byte-identical therefore confirms the data current, without a new
  verification date. A failed, pending or withdrawn run confirms nothing.

A series is **stale** when `now - last_confirmed_current` exceeds its refresh interval.
Legacy-only series (`legacy-unverified`) are always stale (`stale_reason=legacy_unverified`):
legacy rows never confirm currency, however recent their original date. Never-fetched and
never-verified series have `stale=null` with that reason. Distinguish reference-period
coverage, real verification, receipt age, failed attempts and legal queryability in every
audit report.
