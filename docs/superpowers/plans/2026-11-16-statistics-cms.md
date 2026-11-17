# Prumo statistics CMS implementation plan

Date: 2026-11-16
Owner authorization: implement the accepted product direction and update the roadmap.
Authority: ../specs/2026-11-16-statistics-cms-design.md plus the interactive chart design.
Release authorization: not included. No main merge, live schema update or edge deployment.

## Phase A: safe entry and interactive reading

Task A1: Extract and test the shared validated mount-prefix helper without changing public output. Make every backoffice link/action/redirect prefix-aware. Verify direct and /dados/admin forms and hostile-prefix cases. Likely paths: presentation/web.py, app/main.py, backoffice/app.py, backoffice/templates, tests/backoffice.

Task A2: Add optional fail-closed proxy authentication, canonical-origin CSRF and a request actor. Version exact-boundary Traefik/Authelia deployment templates without modifying live configuration. Test missing/forged credential, missing/wrong Remote-User, cross-origin and legitimate writes, no-store, allowed hosts. Record secret provisioning and release order. Depends A1. Paths: backoffice/access.py, backoffice/app.py, deploy, tests/backoffice/test_admin_access.py.

Task A3: Refactor chart preparation with byte-identical SVG evidence; add server chart payload, pinned local ECharts build and scoped CSP. Implement exact pointer/touch/keyboard inspection with SVG/print/failure alternatives on comparison and primary/calculated detail. Keep summary output unchanged. Correct explicit invalid UTC-day selection as specified. Independent file ownership from A1/A2: app chart files/reads/detail templates/static/tooling/tests/app. Resolve any main.py integration only after concurrent work ends.

Checkpoint A: focused Python tests, reproducible asset build, real browser interaction and independent specification review then quality review; no release.

## Phase B: document lifecycle

Task B1: Refactor shared eligibility/plot preparation for reuse before new behaviour. Add typed bounded page/chart documents and migration0019 with immutable revisions, draft/live pointers, version CAS and actor/reason audit. Restrict writable tables; no changes to0018. Verify populated upgrade, rollback on failure, conflicts, immutable content and observation-write refusal. Paths: ingest/cms.py, ingest/db.py, ingest/migrations/0019_statistics_cms.sql, tests/ingest.

Task B2: Implement services and public same-snapshot document reads. Charts reuse public value/provenance/scale logic, no second implementation. Eligibility at publish and render; show chart usages; restore to draft, publish atomic. Tests assert rights revocation and source-data fingerprints. Depends B1.

Task B3: Implement labelled HTML page/chart editor forms, add/move/remove blocks, revision history, preview, duplicate, publish/unpublish/restore. No JSON editing requirement. Mount-prefix and proxy actor apply to every endpoint. Wire /paginas and /graficos public routes plus section listing links and footer Admin link. Depends A1/A2 and B2.

Checkpoint B: execute complete editor-to-public-reader lifecycle, both mount prefixes, empty/invalid/withheld references, conflict and no-write-on-error. Independent specification then quality review and scoped fixes before proceeding.

## Phase C: integrated acceptance and handoff

Task C1: Obtain a fresh read-only backup copy through the existing SQLite online-backup path; migrate the copy, compare integrity/FK and protected table fingerprints, exercise CMS workflow. Measure representative public route median/p95 and chart bundle/payload sizes. Test screens at320/390/768/1440, point inspection first/interior/last, keyboard, UTC, no-JS/blocked-bundle/print and security. Record any unexercised human screen-reader gate explicitly. Depends A/B.

Task C2: Freeze executable tree; controller runs .venv-ci/bin/python -m pytest tests -q and .venv-ci/bin/ruff check app/ ingest/ presentation/ backoffice/ tests/. Independent whole-feature reviews are read-only with bounded probes. Fix blockers and rerun affected checks and full-suite after runtime changes.

Task C3: Update operations with tested provisioning/deployment/rollback instructions; repair superseded next-migration references; update HANDOFF and /home/joao/vaults/projects/prumo/roadmap-e-implementacao.md with actual commits, evidence, pending deployment and future features. Commit/push only scoped reviewed work on pipeline-rebuild. Final report distinguishes local feature acceptance, remaining gates and what is actually online.

## Operational contract

Development databases stay in runtime scratch, never production. No raw docker run/compose. Migration release requires worker then web then backoffice and pre-migration recovery point; public Admin ACL must be effective before exposing the router. Secrets remain encrypted/outside git. Existing fetched/verified/legal gates and original publisher bytes remain intact. Do not implement the AI add-on or operational data-mutating controls in this cycle.
