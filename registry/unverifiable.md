# Sources with no established independent verification channel (spec §6b) — NOT SERVED

A source listed here cannot pass verification **as currently configured in the registry**, so its
runs must never happen or never reach `verified`: `run_with_refetch` raises
`NoVerifierRegistered` when no verifier is registered for the source, and raises
`SourceNotVerifiable` up front — before any fetch, parse or HTTP request — when the source is
marked `verifiable: false` under `sources:` in `registry/core.yaml`. Inactive series
(`active: false`) are additionally excluded from T17/T18 scheduling altogether.

## dgeg — `verifiable: false` since Task 12B (2026-11-11), a SCOPED marker

DGEG today has **no ingest adapter and no verifier**, and **no new live DGEG collection** has
run. The Task-8 legacy import is retained unchanged and remains legacy-unverified. The marker
is an eligibility block on the 17
DGEG series **with their current core definitions** (units, coordinates, concepts): under those
definitions no independent exact verification channel is established. It is not a claim that an
independent channel is impossible or that DGEG "has no source": the bounded 2026-11-11 research
(controller-verified hashes, `docs/superpowers/handoff/evidence/task-12-dgeg/`) found genuine
partial same-publisher channels (APN/AEN PDFs and a same-format quick-stats workbook) with per
series unit conflicts, vintage drift, base-year mismatches, representation-policy and coverage
gaps. Per-series coordinates, findings and resumption criteria: `registry/unmapped-dgeg.md`.
An earlier Task-10-era wording here implied such sources "still collect data and raw evidence" —
that did not describe live DGEG collection and is corrected: an adapter and verifier must be
explicitly implemented and reviewed before new live collection; the legacy import is separate.

## Status of the other core sources

- **ine** — verified (`ingest/verifiers/ine.py`, bddXplorer table channel) and served normally.
- **bportugal, eurostat** — `verifiable: true` with registered verifiers.
- **ren** — independently **verifiable** (`ingest/verifiers/ren.py` CSV export channel) but
  licence-withheld: `redistribution_ok: false` keeps every verified row at served=0 under the
  0005 gate. Withheld ≠ unverifiable — REN does not belong in this register.
