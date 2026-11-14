# Prumo — Backoffice (project 2) — Design

Date: 2026-11-14 · Status: written by the planner from the owner's instruction "avança com backoffice" (owner opted out of the question round; every choice below is the planner's call unless marked **[owner]**).

## 1. Intent and why

The base pipeline (project 1) is deployed and verifying 1,344 series, but everything about its health is visible only through the terminal (`python -m ingest status|lag|verify|withdraw`) and raw SQL. The owner's single promise to the public is trust; the person responsible for that promise (the owner, later possibly a statistician reviewing the data) needs a place to **see at a glance whether the data is healthy, why any number is or is not served, and to act on problems** without hand-written SQL. Spec section 2 of the pipeline design already names it: "review of flags, source health, indicator registry".

## 2. Goals

- G1. One screen answering "is everything fresh and verified right now?" (per source and total: active, stale, never fetched, pending verification, blocked by licence/verifiability, last verified, next scheduled attempt), consistent with `ingest status`.
- G2. Per-series provenance view: for any series show registry spec, licence/attribution, served vintage, raw payload hash and source URL, retrieval time, revision history (vintages), quarantined rows with reasons, and the verification items that covered it (value, evidence, reason drawn, replay result). This is the future UI's "where does this come from" view, prototyped for the owner/auditor.
- G3. Review queues: events needing a human (verification failures/escalations, revisions above threshold, new-period gaps, `ingest lag` hits, quarantine reasons, licence-withheld sources, stuck pending-verification runs), each with a status (open / acknowledged / resolved by owner, with a note).
- G4. Registry view: all series (active/inactive, reason for inactive from `registry/unmapped-*.md`), filters by source/theme/geography/frequency; read-only (registry stays authoritative in git).
- G5. Audit trail: every action taken in the backoffice is an event row in the DB (who, when, what, reason).
- G6. Replay for auditors: run `replay_item` for a verification item from the browser and show match/mismatch with the evidence bytes.

## 3. Non-goals and anti-goals

Non-goals (v1): editing the registry in the browser; triggering fetches; any public access; the derived layer; the public UI (project 4); users/roles beyond the owner; push alerts (owner decision: none).
Anti-goals — failure even if it works: the backoffice becoming a second path that can change served data without an audit event; a view that disagrees with `ingest status`; anything that can corrupt or lock the production DB; being reachable from the public internet.

## 4. Planner's calls

1. **Read-only first, actions second.** v1 is entirely read-only (opens the DB through the existing `open_db_readonly`, so it can never write or migrate and cannot disturb the worker). v1.1 adds exactly three audited actions that already exist in the CLI: `acknowledge/resolve` a review-queue item (note only), `withdraw run` (calls `Db.withdraw_run`), and `verify run`. Each writes via the same db.py functions the CLI uses, never SQL in the web layer, with a confirmation step and a mandatory reason. Deactivating a series stays a registry/git change.
2. **Where it runs:** a separate container `prumo-backoffice` from the same image, a separate FastAPI app (`backoffice/`), bound to the Tailscale address only (e.g. 100.118.19.6:8089), **no Traefik/public route**. Auth: Tailscale network membership is the perimeter [planner's call; owner may add a login later]. It shares the DB volume read-only (`:ro` mount) in v1 so a bug cannot write; v1.1 gets a second small read-write mount only for the audited actions or goes through the worker's CLI via `docker exec` (decide in the plan).
3. **Stack:** Python/FastAPI + Jinja2 server-rendered pages + a little vanilla JS; no frontend build step, no SPA. Reuses `ingest/status.py`, `ingest/data_lag.py`, `ingest/db.py` read functions (new read functions are added in db.py, never SQL in the web layer, per the project rule). Style deliberately plain and dense (tables, filters), because the UI revamp is project 4; no charting library in v1 except tiny inline sparklines for a series' vintages if cheap.
4. **Review queue storage:** a new small table (migration 0014) `review_item(id, kind, ref, opened_at, status, note, resolved_at)` populated by a read-time/derive step rather than by the pipeline, so the pipeline stays untouched. Items are derived from events and status; the backoffice only stores the owner's acknowledgement and notes.
5. **Deployment during the 24 h observation of Task 18:** build and test on a branch; deploy only the *new* container (`dc-web-up prumo-backoffice`); never restart `prumo-ingest` for it. Migration 0014 is additive and is deferred to the next planned worker deploy (the backoffice v1 does not need it; queue state in v1 is derived/ephemeral).

## 5. Parts (build order)

1. Read layer: db.py read functions + tests for: overview, series list/filter, series detail + vintages, quarantine, events, verification items + replay result.
2. App skeleton + health + overview page + series list + series detail (provenance) + events/queue pages.
3. Compose file `compose/prumo-backoffice.yml` (own file per convention), Tailscale-only bind, `:ro` data mount, healthcheck; docs in docs/data/operations.md.
4. v1.1 audited actions (needs migration 0014 and the write path decision) — separate plan after v1 is in use.

## 6. Constraints

All existing rulings stand (numbers are publisher token strings, never floats; SQL only in db.py; nothing invented). Test-first. No secrets in the repo or compose; dc-* aliases for containers; `compose/<service>.yml` per service. The backoffice must render correctly with an empty/never-fetched DB and with a DB whose schema is older/newer (refuse with a clear message like `status`).

## 7. Left to the builder

Page layout details, filter UX, pagination, the exact derived-queue rules and thresholds (start with: any `verification_failure`/`verification_escalated` in 7 d, `new_periods` gaps, revisions > N% for a series, `lag` hits, pending > 24 h, blocked sources), caching, and test fixtures (reuse the production-shaped fixtures).

## 8. Open questions for the owner (non-blocking)

Is Tailscale-only access enough or do you want a login? Do you want the audited write actions at all in the first release? Should a statistician (external) ever get a read-only view (would need auth and a public-safe subset)?
