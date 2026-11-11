# Sources with no independent verification channel (spec §6b) — NOT SERVED

A source listed here has an adapter (fetch → raw store → validation) but no channel independent
of the collector's own parser through which a sample can be re-read. Its runs therefore never
reach `verified` (no verifier is registered for it: `run_with_refetch` raises
`NoVerifierRegistered` before fetching, and a `verifiable: false` marker under `sources:` in
`registry/core.yaml` makes `run_with_refetch` refuse it outright), so `served_observation` never
shows its data. Data and raw evidence are still collected, so revision history starts at the
first ingestion. Owner decision needed.

**No source is unverifiable today.** INE was listed here provisionally (Task 10 first pass) but
the review found the channel: `bddXplorer/htdocs/bddXplorer04.jsp`, INE's server-rendered
statistical table, works over plain HTTP with a `Referer: https://www.ine.pt/` header (a plain
client without it gets 302 + empty body, which had been misread as "browser-only"). INE is
verified by `ingest/verifiers/ine.py` (Task 10 fix round 1) and is served normally.
