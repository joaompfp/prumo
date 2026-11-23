# SQLite worker safety release installed (2026-11-23)

## Installed scope

Owner explicitly requested installing the pending worker-incident correction and restarting ingestion after the separate phase B UI release. Runtime/main `3ab1fdcad3c40fc2a9e7dc5e3fa9fe32f6cfe547` combines installed main `4719f55` with the already reviewed operational commits through `68609ef`. No phase B runtime file was removed or changed. Public web, Admin and worker all package the corrected `ingest/db.py` and were therefore replaced together.

The worker now has `PYTHONFAULTHANDLER=1`. Every read-only opener uses canonical sidecars and unconditional `readonly_shm=1`, refuses reader recovery and bounds immutable retries to actual writer evidence. This closes the reproduced reader-side shared-memory mutation defect. It does NOT establish the historical trigger for the old SIGBUS exits.

No migration, source parser, licence, source-data edit, CMS edit/publication, ownership, credentials, authentication or shared-edge change ran. Normal automatic ingestion remains enabled.

## Verification gates

The prior specification and quality approvals for `fe13837` were retained. A fresh read-only final integration review approved the combined release and independently demonstrated the old/new shared-memory effect, read-only descriptor access and missing-sidecar refusal. The controller separately exercised 71 focused tests from the actual detached committed checkout with local imports checked; broader ruff passed. This is not represented as another whole local suite.

Exact-main hosted CI [45138023772](https://github.com/joaompfp/prumo/actions/runs/45138023772) passed on the installed runtime: 3,206 passed, 29 skipped, seven live tests deselected, three warnings in 571.29 seconds. Lint passed. Workflow Node-action and post-checkout cleanup annotations did not fail either job; no CI-workflow change was included.

Production acceptance after replacement passed 41 worker/image/data checks, 1,392 public-browser checks in 104 populated route/viewport/address cases, 25 access/state/Admin checks, 54 checks of the nine real comparison editors and their analytical preview, and ten private homepage-preview checks. Actual installed persistence hashes match the approved commit in all services. Public comparisons still show only published CMS revisions. Browser application errors and off-origin requests are absent; the existing shared-edge `vr` Permissions-Policy warning remains (112 occurrences in this matrix).

At activation every table fingerprint matched: 635,430 observations, 34,343 quarantined rows, 1,791 series, 10,145 stored derived observations, 12 CMS documents, 15 CMS revisions and 29 CMS events. Stored derived history is NOT the current served-value count. Schema/migration hashes are unchanged, quick integrity is ok and foreign-key violations are zero. Source retrieval timestamps were not rewritten. All unrelated tracked infrastructure edits were hash-compared and preserved.

## Activation and recovery

Operator directory: `f0nix:/home/joao/prumo-operations/worker-safety-release-20261123`.

Prebuilt the exact release from a detached context using `dc-web` before touching live bind mounts. All three old actual images were pinned. Confirmed no source run in flight; stopped/read back all three services; fast-forwarded the clean live checkout; installed only the reviewed worker include; then used normal `dc-web-up` aliases in worker/public/Admin order. Active services:

| Service | Container | Actual image | Started UTC |
|---|---|---|---|
| Worker | `fd1f7b57` | `8679a19d` | 2026-11-23 08:32:43.627785908 |
| Public | `9a57ad8e` | `f5c6c991` | 2026-11-23 08:32:44.879464233 |
| Admin | `9dd2b77c` | `b303b4ac` | 2026-11-23 08:32:46.125265314 |

Worker has no HTTP healthcheck by design. Its actual command/uid, startup scheduler pass, current DMS lock, active fatal-fault configuration and successful read-only CLI status were checked. The readers are healthy. CLI status reports 1,344 active series, zero never-fetched/never-verified/stale series and zero stuck pending verifications. No fresh collection was due during the initial checks, so that state is NOT claimed as a new verification of all sources.

The exclusive-created online recovery copy was independently reopened: `/home/joao/prumo-operations/worker-safety-release-20261123/prumo-before.sqlite3`, 300,126,208 bytes, SHA-256 `e415fafece955fe5832701bc3ad8efaef80c20502632d584f000332317d96b95`, full integrity ok, zero foreign-key violations. Do not restore it over newer production data for a schema-compatible code rollback.

Recovery checkout is actual previous main `4719f55`, not the older pre-phase-B baseline. Retained exact tags: `prumo-ingest:rollback-worker-safety-20261123` (`ff50b981`), `prumo:rollback-worker-safety-20261123` (`6022e973`) and `prumo-backoffice:rollback-worker-safety-20261123` (`90cfbfae`). Saved old worker include: `prumo-ingest-before.yml`. Stop the bind-mounted public reader and both writers before changing the runtime checkout; recover the recorded code/images through the established `dc-web` aliases, preserve the database/history and diagnostics, and verify the actual image ids. Never advance backwards on remote main, replay a prebuild context override for `up`, unlink live sidecars or restore source data to downgrade code.

## Observation gate

The initial real scheduler interval completed at 08:48 UTC: 917.064146 uninterrupted seconds, same worker identity/start and zero autonomous restarts. The collector ran successfully through systemd in the same operator execution context as the future timer. The final 42 checks passed and every table fingerprint still matched. No source or derived run was due during this interval; no new retrieval or verification is claimed. The old three autonomous restarts remain historical evidence, distinct from the new container's count. See `release/observation-15min.json` and `release/final-acceptance.json`.

The exact activation shell also passed four stubbed control-flow scenarios (success, failed stop, failed stopped-state readback and failed checkout), proving the latter failures cannot proceed to installation/start. The observation gate passed independent age/replacement/restart refusal probes. These are operator-helper tests, not another application-suite result.

A local-only, no-agent evidence collector is scheduled on f0nix for 2026-11-24 08:35:00 UTC, after the earliest uninterrupted 24-hour point at 08:32:43.627785908 UTC. System timer: `prumo-worker-safety-evidence-20261123.timer`; the service runs as `joao:joao` and writes `observation-24h.json` in the operator directory. Exact timer and service arguments were read back. This is evidence collection, not automatic incident acceptance; no messages or automatic backups are configured. An early 24-hour attempt was exercised and correctly refused. A replaced/restarted worker is also refused rather than accepted based on a new zero count.

Root-cause closure and 24-hour acceptance remain OPEN. Later review must inspect uninterrupted identity/age, actual source/derived outcomes and daemon/fatal diagnostics. Human screen-reader acceptance, source rights/DGEG and product phases C/E remain outside this repair.

## Retained checker failures

Initial clean-checkout command had shell quoting and an incorrect `backoffice.main` import; corrected to the actual `backoffice.app` entrypoint before running the committed-tree gate. No application change was needed.

The first prebuild comparator treated the order of the two Admin mounts as meaningful. Docker returned the same `/data:ro` and `/data-w:rw` mounts in a different order; exact service identity/image/start/restarts and all source/target/rw fields were unchanged. The corrected comparator sorts by mount destination and passed against the SAME retained receipts. No prebuild or healthy service was restarted to repair this checker.
