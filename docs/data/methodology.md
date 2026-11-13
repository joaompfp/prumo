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

Sampling includes the latest available period of every populated series in the run,
then random historical observations without replacement. The default target is 50;
it grows to at least one observation per populated series and is bounded by available
rows. If series count consumes the target, no additional historical rows are drawn.
The stored seed makes the selected sample reproducible for the same run and size.
A series with no accepted rows cannot be sampled and requires the coverage review above.

Every sampled item must match: exact series/period identity, exact `Decimal` numeric
value with no tolerance, and unit/status flag when the independent channel exposes
them. Different trailing zeroes can compare numerically equal. Missing results,
wrong result count or order, parsing errors and mismatches fail verification. A
100% sampled match is mandatory; it does not independently prove every unsampled row.
A separate full-row check against archived collector bytes, when performed, has a
different evidentiary scope and must be reported separately.

A failed verification keeps that run out of the served view and triggers a full
refetch of its dataset group with a fresh seed, up to three total attempts by default.
Fetch/validation failures return their own failure state; scheduler retries are a
separate policy. World Bank runs are grouped per indicator across all its registered
active geographies; other sources run their active series as one dataset. A failed
World Bank indicator does not stop healthy siblings.

There is an accepted exception to fresh sampling: responses with the same fingerprint
as the immediately previous verified run of the same dataset short-circuit to
`verified`, with no new observations or verification sample. Prior verified rows stay
queryable; no new independent verification date is invented. Identical bytes after a
failed run are fully processed again.

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
rebuild command. The `replay_item` Python helper rechecks stored comparison fields and
hashes without network; independently reparsing archived evidence is a further audit.

Original-file imports use validated `capture` bundles for World Bank/E-REDES only.
All attempts are marked `input_origin=recorded`; original collector receipt times
remain the data's `fetched_at`, while processing time stays current. Older recorded
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

Status staleness uses the implemented refresh policy, based on actual retained-data
retrieval dates and registry schedule/frequency. It is not proof of the publisher's
latest possible release. Distinguish reference-period coverage, real verification,
receipt age, failed attempts and legal queryability in every audit report.
