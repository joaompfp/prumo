# Prumo image and ingestion operations

## Current public interface: phase B shared analytical reading

Owner-authorized main/runtime `5346447` is installed on f0nix from 2026-11-21 21:36 UTC. Exact point inspection uses structured period/series/value rows; primary/calculated/CMS charts share the analytical layout. All nine comparisons remain CMS-authored and public read-only; the separate Caderno retains exploration. Only web and Admin were recreated, healthy with zero restarts. No migration, CMS/source-data write, worker or authentication/shared-edge operation ran.

Exact-main CI `44951525399`: 3,193 passed, 29 skipped, seven live deselected, three warnings. Fresh clean-checkout tests: 84. Installed public browser: 1,392 assertions in 104 cases; nine Admin editors/static chart preview: 54; state/access: 33; static home preview: ten. Schema/migrations and every CMS table fingerprint match pre-activation. Worker remains container `39214757`, image `ff50b981`, start 2026-11-21 15:04:10 UTC and three pre-existing autonomous restarts. Its incident fixes on `pipeline-rebuild` remain separately pending, not part of this UI release.

Recovery checkout `34ed8c0`, pinned images `prumo:rollback-analytical-reading-20261121T2122` and `prumo-backoffice:rollback-analytical-reading-20261121T2122`. Stop only the affected bind-mounted public reader before changing its checkout, then rebuild/recreate the two readers through the established aliases. Preserve the database, authored content and worker. Exact receipts, safe read-only probe and executed installation helpers: [installed phase B](../superpowers/handoff/reports/analytical-reading/installed.md). Human screen-reader acceptance and the existing shared-edge vr warning remain open. Later report-only commits do not require rebuilding healthy services.

## Previous public interface: grouped two-axis notebook and Portugal comparisons

Owner-authorized runtime/main `3aac922` is installed from 2026-11-20 22:33 UTC. Public web `31dcfe0b` and Admin `c5709790` are healthy with zero restarts. The Caderno supports up to six series in two compatible raw scale groups and `/comparar` has reviewed Portugal configurations. Pair links, native/annual views, exact source values and one-axis transformations retain their contracts.

Exact-main CI `44828613494` passed: 3,114 tests, 25 skipped, seven live deselected. Clean committed checkout: 144 tests; installed browser: 38 scenarios / 876 assertions; state/Admin: 33; static preview: ten. Schema0019/migrations and all CMS content/history fingerprints are unchanged. This was reader-only: no source-data write, migration, publication or worker/shared-edge/auth change. The worker baseline already included one autonomous restart at 21:39 UTC; it did not change during deployment. Cause/operational observation and human screen-reader acceptance remain separate.

Recovery checkout `68f6799`, pinned reader tags `rollback-multiscale-20261120`; preserve database and worker. Stop the bind-mounted public reader before restoring its checkout, then restore affected readers using the established aliases. Never activate using the context-only prebuild override. Exact evidence, scripts, images and remaining scope: [installed grouped scales](../superpowers/handoff/reports/multiscale/installed.md).

## Previous public interface: notebook time alignment and analytical transformations installed

Owner-authorized main `7690837` is installed on f0nix from 2026-11-20 18:15 UTC. Public web `3ecad22a` and static-preview Admin `6e14cef1` are healthy with zero restarts. Mixed A/S/Q/M/D originals share an honest native calendar; annual harmonisation, base100 and percentage-point views require explicit valid methods/base. Source data, schema0019/migrations, worker identity/image/start/restarts and authored CMS/history remain unchanged. No migration, publication, worker/edge/authentication change ran.

Exact-main CI `44789496972` passed (3,075 passed, 19 skipped, seven live deselected); 287 clean committed-checkout tests, 115 installed public browser checks, 33 state/Admin and ten preview checks passed. Human screen-reader acceptance remains separate. Reader methods and safe limitations: [Caderno](notebook.md). Full deployment, checks, retained failures and recovery: [installed transformations](../superpowers/handoff/reports/time-transformations/installed.md).

Retained recovery: actual previous checkout913eb2f; images prumo:rollback-time-transformations-20261120 and prumo-backoffice:rollback-time-transformations-20261120. Public app/static are live read-only binds: stop only the affected public reader before changing runtime checkout, restore code and readers through existing aliases; do not restore the database or restart ingestion for a UI rollback. Prebuild used a detached approved-main context and a build-only dc-web override; activation used normal dc-web-up aliases. Only actual new image/tag/rollback relations are acceptance checks; regenerated outer OCI attestation ids are not executable equality. Subsequent documentation commits do not require rebuilding working images.

## Previous public interface: analytical notebook workspace installed

Owner-authorized main `913eb2f` (runtime `050d69e`) is installed from 2026-11-19 16:55 UTC. Public web `4c3def73` and static-preview Admin `2cd23e48` are healthy/zero restarts. The notebook is plot-first, grows across wide monitors, keeps common/latest periods distinct and exposes nearby native add/configure actions. Only the readers changed. Complete worker baseline, schema/migrations and CMS/history fingerprints match pre-activation; quick_check ok, no FK violations. No data/content writes, migration, ownership, credentials, edge or worker restart.

Exact-main hosted CI `44569621926` passed (2,847 passed, nine skipped, seven live deselected); fresh clean-commit release gate 100 tests, installed public browser 459 checks, state/Admin 33 and private preview ten passed. Human screen-reader acceptance remains separate. The existing shared-edge vr warning is unchanged. Recovery: actual previous checkout `361eca7`, retained reader tags `rollback-analytical-workspace-20261119T164616Z`; restore checkout AND images because app/static are live binds, preserve database/history/worker. Prebuild used a detached context before stopping only public web for activation through the normal dc-web-up aliases.

An initial checker compared outer OCI index ids and failed after healthy activation due to regenerated BuildKit attestations. The archived exporter receipts prove platform runtime manifests and configs are identical to prebuild; actual container/tag/rollback relations were verified separately. No runtime correction or second activation ran. Do not compare attestation-bearing outer indices as proof of executable build equivalence. Full evidence/recovery: [analytical workspace installation](../superpowers/handoff/reports/analytical-workspace-release/installed.md).

## Previous public interface: notebook charts and grouped navigation installed

Owner-authorized main361eca7 (runtime7baa127) is installed on f0nix from2026-11-18T07:51 UTC. Public web660146a8 and Admin09da694b are healthy/zero restarts. Caderno supports up to six selected series on a common or explicit two-side dual scale; up to twelve cards remain. Native grouped navigation/search and the static CMS preview share the new shell. Schema0019/migrations, CMS contents/history and the full worker identity/image/start/restarts match pre-activation. No migration, content/source-data write, credentials or shared-edge change. Exact-main hosted CI44260267298 passed;95 fresh committed-tree checks,2117 public browser checks,33 Admin/state checks and10 preview checks passed. Human screen-reader acceptance remains separate.

Public app/static are live bind mounts: do not advance their checkout while prebuilding. This release prebuilt from a detached approved-main context through a temporary dc-web build override, then briefly stopped only public web before fast-forwarding its clean live checkout and recreating web/Admin through normal dc-web-up aliases. Never use the build-only override for up. Match each pinned rollback tag to the running old image before activation and actual rebuilt runtime tags to container images afterwards. Recovery code24a3dc7 and retained web/Admin tags rollback-notebook-navigation-20261118T074000Z preserve DB/history/worker. Actual edge transfer180001 gzip wire bytes; existing vr warning and stricter global robots header are unchanged. Full records and precise recovery: [notebook/navigation installation](../superpowers/handoff/reports/notebook-navigation-release/installed.md).

## Historical candidate: legibility and indicator notebook

The new type scale, local licensed fonts, native mobile navigation/editor outline and stateless Caderno are implemented on pipeline-rebuild at code f291ae2, not installed. The full controller suite passed2,717 tests with7 network deselected;783 browser checks and485 type measurements passed, with20 protected tables unchanged. This is a schema-unchanged public-web/backoffice release only. No CMS initialization/publication or worker, authentication, ownership or shared-edge change is required. Use the existing dc-web schema-unchanged procedure and pin both currently installed images first. Rollback changes only those two code/images; retain all data and CMS history. The current installed baseline remains the Tabler/carmim section below. Acceptance: [legibility/notebook report](../superpowers/handoff/reports/legibility-notebook/README.md); reader instructions: [Caderno](notebook.md).

## Previous Tabler/carmim interface: installed 2026-11-17

Runtime 14f845e is merged, pushed and installed after owner approval and hosted CI 44090471137. Public web was recreated at 13:20:58 UTC and backoffice at 13:21:00; both healthy, zero restarts. Worker identity/image/StartedAt/restarts are exactly unchanged. No migration, source-data/content write, ownership, credentials or shared-edge change. Schema remains 0019, next free 0020.

Final gate: 2,688 tests passed, 7 network deselected, 3 warnings; ruff and Admin JavaScript syntax clean. Local production-copy acceptance passed 205 browser checks and 17 measured colour groups, preserving all 20 non-CMS fingerprints. Installed acceptance passed 90 public and 33 trusted-proxy/state checks. CMS content/history and schema fingerprints match the pre-release state; quick_check ok, zero FK violations. No trial content was published live.

Edit the current homepage at https://joao.date/dados/admin/cms/page/inicio. Installed images, recovery tags, evidence and known shared-edge warning: [Tabler/carmim installation](../superpowers/handoff/reports/tabler-ui/carmim-installation.md). This is a schema-unchanged release: recover old web/backoffice code 7a35f47 and pinned images through the existing dc-web aliases, without a database restore or worker restart. The earlier homepage creation and combined-migration records below are historical.

## Previous homepage/UI extension: installed 2026-11-17

Runtime b842199 is installed on f0nix after owner authorization. Public web and backoffice were recreated at 09:55:52 and 09:55:53 UTC; worker identity/image/StartedAt/restarts are unchanged. No migration, ownership repair or shared-edge change. Schema 0019, next free 0020. Hosted CI 44055444383 passed on this SHA; fresh release checks: 92 passed, ruff/JS syntax clean.

The complete current homepage was created and published at 09:57:20 UTC: page/inicio version 2, revision 6,17 ordered blocks and audit events 10/11. All 20 non-CMS table fingerprints and migrations matched before/after publication, quick_check ok and zero FK violations. The public Chromium smoke passed 113 checks across both mounts and four widths;17 trusted-proxy Admin checks passed. The public editor URL still challenges through Authelia. Human login/publication and screen-reader acceptance are distinct from this technical proof.

Edit at https://joao.date/dados/admin/cms/page/inicio. Installation/image/rollback evidence: [installed home CMS/UI](../superpowers/handoff/reports/home-cms-ui/production-installation.md); machine receipt is alongside it. Follow the authoritative [cms.md](cms.md) procedure for future initialization and schema-unchanged rollback. Preserve authored history, and do not restore source data to downgrade a content shape. A public-only Permissions-Policy vr warning remains a shared-edge follow-up; no edge change ran here. The combined-migration baseline below is historical, not this release procedure.

## Installed product baseline (2026-11-17)

Application release installed 2026-11-17 at 01:45 UTC: runtime code f493045,
schema0019, worker then public web then backoffice. Fresh controller suite2580 passed,
7 deselected, ruff clean; hosted CI43996469531 passed on that SHA. Three containers running,
zero restarts, both public health routes200. The recovery copy is on f0nix at
/home/joao/prumo-operations/cms-release-20261117T012653Z/prumo-pre-0019.sqlite3
(217,403,392 bytes, schema0018, integrity ok, zero FK violations). Old code c9a2e5f and
all three previous images are recorded and pinned. BPstat/E-REDES/FRED collection resumed;
E-REDES added291 observations, so scheduled runtime changes must not be mistaken for
CMS writes or claimed unchanged.

Admin activation completed at 01:58:12 UTC after renewed owner approval, through
`bash -lic 'dc-core restart traefik'`. All 54 routers are enabled, including
`prumo-admin@file`. The anonymous Admin request receives the Authelia login redirect locally
and from f0nix through the public IPv4 address. The direct backoffice still returns 401;
all 17 internal access/CSRF checks passed. The technical CMS trial completed 28 checks,
including public readback on both prefixes, private-draft isolation, stale-form refusal,
restore and final unpublication of the page/chart; the database retains 9 audit events.
This was a trusted internal-proxy probe, NOT a real human Authelia login. The browser
showed the Authelia login portal; owner login/publication acceptance remains open.

The combined migration release/rollback contract is [cms.md](cms.md); edge details are
[README-admin.md](../../deploy/README-admin.md). Rollback needs old code AND the pre0019
DB, with writers stopped. Current resume details and exact image/start times are in
[HANDOFF](../superpowers/handoff/HANDOFF.md). Live chart inspection verified the canvas,
keyboard period selection and exact readout; the installed local bundle returned gzip,
179,641 wire-body bytes. This scoped smoke test does not repeat the full development browser
matrix. Human owner/screen-reader acceptance and separate rights/DGEG/worker-observation
obligations remain open. Operational data-write actions stay outside CMS; next free migration
0020. See [production activation](../superpowers/handoff/reports/statistics-cms/production-activation.md).

## Historical pipeline deployment and operating procedures

The maintenance web app `prumo` and ingestion scheduler `prumo-ingest` are already
deployed on f0nix. Task 18 runtime merge `49a3602` and infrastructure commit `6a58b51`
were installed after owner authorization and release checks. This runbook describes
that deployed contract and separately authorized future maintenance; it is not an
instruction to redeploy or repeat bootstrap during the open observation.

The real 24-hour observation remains open. It started at
`2026-11-13T01:21:18.732242+00:00` and cannot finish before
`2026-11-14T01:21:18.732242+00:00`. The local-only evidence job `41f08dd25c5c`, scheduled
for `2026-11-14T01:24:32.992446+00:00`, collects receipts, not acceptance. Keep both
services unchanged during the window. No push alerts or automatic backups are part
of this procedure. Final Project 1 acceptance belongs to the owner.

Terminology: CLI means command-line interface; HTTP means Hypertext Transfer Protocol;
UTC means Coordinated Universal Time; CSV means comma-separated values; JSON means
JavaScript Object Notation; SQL means Structured Query Language. SOPS is the encrypted
secret editor used by the infrastructure stack. FRED, OECD, REN and DGEG publisher
identities and licence metadata are listed in the [source catalogue](sources.md).

## Deployed paths and intermediate checkpoint

| f0nix host path | Container/runtime use |
|---|---|
| `/home/joao/docker/stacks/web/images/prumo` | Installed app checkout |
| `/home/joao/docker/stacks/web/compose/prumo-ingest.yml` | Worker include in the existing web stack |
| `/home/joao/docker/stacks/web/appdata/prumo` | Persistent shared `/data` volume |
| `/home/joao/docker/stacks/web/appdata/prumo/prumo.sqlite3` | `/data/prumo.sqlite3` |
| `/home/joao/docker/stacks/web/appdata/prumo/raw` | `/data/raw` |
| `/home/joao/prumo-operations/task18-49a3602` | Durable operator receipts, also retained on f3nix |

Production is f0nix, not an isolated database under the f3nix working checkout. Public
GET checks use `https://cae.joao.date/` and `https://joao.date/dados/`; the maintenance
listener is `100.118.19.6:8088`. HTTP health alone says nothing about source freshness.

The controller's [Task 19 brief](../superpowers/handoff/reports/task-19-brief.md)
records an intermediate snapshot at `2026-11-13T08:36:38.064186+00:00`. This document
has not independently recollected production evidence. At that checkpoint the worker
was running with zero restarts/OOM, SQLite integrity passed, licence-gate violations
were zero and the original 161,263 legacy-row fingerprint and old DuckDB hash were
unchanged. All 1,345 active series had real successful automatic verification and
none was stale under the implemented refresh policy. This does not prove that every
publisher had released the latest possible period or complete the observation.

| Source | Checkpoint disposition |
|---|---|
| BPstat (Banco de Portugal) | 4,318 current fetched rows queryable |
| E-REDES | 64,479 current fetched rows queryable; native history ends `2026-11-11T00:00:00+00:00` |
| Eurostat | 45,500 current fetched rows queryable |
| INE (Instituto Nacional de Estatística) | 12,034 current fetched rows queryable |
| World Bank | All 18 indicator groups / 930 active series verified from live input; 45,915 current fetched rows, 949 matching samples across the successful runs |
| FRED / OECD / REN | 12 / 6 / 14 active series technically verified, respectively; withheld by `redistribution_ok=false` |
| DGEG | 17 inactive definitions, `verifiable=false`, no new adapter; reuse rights unresolved |
| ERSE | Zero core definitions |
| dadosgov | Historical/unresolved integration retained; no stored-data claim |

World Bank recovered automatically at that checkpoint, with no legacy World Bank rows
remaining in the current served view. Its earlier 17 failed fetches and 9 failed
verification subruns remain history. Do not erase them or infer permanent endpoint
reliability; scoped dated-data continuity remains enabled if needed. Original legacy
rows and receipts are preserved. The [methodology](methodology.md) describes the
sampled-match limits and the distinction between verification and redistribution.

Exact checkpoint receipts under the operator directory are
`status-20261113T083638Z.json`, `audit-20261113T083638Z.json`,
`summary-20261113T083638Z.json` and `worker-20261113T083638Z.log`. The controller owns
archiving and review; [HANDOFF](../superpowers/handoff/HANDOFF.md) and the
[Task 18 release report](../superpowers/handoff/reports/task-18-controller-review.md)
retain the earlier deployment record. Those earlier source outcomes are not a later
all-source snapshot.

The image contains `app/`, `static/`, `ingest/` (including migrations) and `registry/`.
Historical collectors, scripts and seeds remain in the repository but are excluded from
both the build context and the image. Keep all credentials outside these runtime directories;
`.dockerignore` excludes environment/credential files even inside the allowed directories.
Never pass secrets as build arguments or bake them into source files.

## Installation contract for a future authorized rebuild

These prerequisites were applied for Task 18. They are reference checks for a future
controller-authorized rebuild, not pending installation work. The controller owns
changes to `/home/joao/docker`:

- Install `deploy/prumo-ingest.yml` as
  `/home/joao/docker/stacks/web/compose/prumo-ingest.yml` and include
  `compose/prumo-ingest.yml` in `/home/joao/docker/stacks/web/compose.yml`.
  The existing stack supplies `t2_proxy`, `DOCKER_DIR` and `TZ`.
- Correct the existing web `prumo.base.yml` environment: remove the obsolete `CAE_DB_PATH`,
  set `PRUMO_DB_PATH=/data/prumo.sqlite3` and `PRUMO_RAW_DIR=/data/raw`.
  Retain the maintenance web command, HTTP healthcheck and `100.118.19.6:8088` binding.
  The web image still defaults to uvicorn on container port 8080.
- Remove the obsolete `OLLAMA_BASE`/`ai_net` coupling from `prumo.yml` only under the
  controller's reviewed infra scope. Do not add AI credentials/dependencies to the worker.
- Provision `FRED_API_KEY` in the existing SOPS web secret bundle securely. It is the
  worker's only source secret. Never paste it into chat, command arguments, logs or a
  plaintext file in the image checkout. Do not print decrypted env files or container Env.
- Check available persistent disk space for the original CSV, SQLite and raw response
  archive. Do not delete historical data to make room.

`PRUMO_DB_PATH=/data/prumo.sqlite3` and `PRUMO_RAW_DIR=/data/raw` are the worker/image
contract. Since Task 23 (branch `pipeline-rebuild`) the ingestion CLI reads the same
`PRUMO_DB_PATH`, with the older `PRUMO_DB` only as a deprecated fallback; the deployed
49a3602 image still reads only `PRUMO_DB`. The operator commands below keep passing `--db`
and `--raw-dir` explicitly, before the subcommand, so they are correct for both images.

The worker has its own `prumo-ingest:latest` image tag and no published ports or Traefik
labels. Its inherited web HTTP healthcheck is disabled. A running process is not proof of
successful ingestion; use logs, status and response evidence. No heartbeat is fabricated.

## Bootstrap and initial catch-up

Task 18 already completed the original import and catch-up. Do not repeat this section
against the deployed volume during observation. For a separately authorized first
installation/recovery, use an interactive Bash session on f0nix and preserve a new
evidence directory for later checks and rollback. Stop if the deployment checkout has
local changes; reconcile them with its owner instead of resetting or cleaning it.

```bash
set -euo pipefail
set +x
export OP="/home/joao/prumo-operations/task18-$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 700 "$OP"
cd /home/joao/docker/stacks/web/images/prumo
test -z "$(git status --porcelain)"
git rev-parse HEAD > "$OP/code-before.txt"
docker inspect prumo --format '{{.Image}}' > "$OP/web-image-before.txt"
git fetch origin
git switch main
git merge --ff-only origin/main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
git rev-parse HEAD > "$OP/code-installed.txt"
install -m 644 deploy/prumo-ingest.yml \
    /home/joao/docker/stacks/web/compose/prumo-ingest.yml
```

The controller now applies the prerequisite include/web-path/dependency edits above.
For secret provisioning, open the encrypted bundle with the existing SOPS editor workflow;
the value must not be placed in a shell command. Verification below is silent on success
and does not expose any secret. It must succeed before either build/start alias is used.
The read-only `dc-web` alias does not decrypt secrets, so a successful config check alone
does not establish that FRED is configured. Optional `${FRED_API_KEY:-}` interpolation in
the worker definition deliberately allows that read-only alias to work.

```bash
cd /home/joao/docker
# Controller only, if the key needs provisioning:
sops secrets/web.enc.env
sops exec-env secrets/web.enc.env \
    'python3 -c "import os; raise SystemExit(0 if os.environ.get(\"FRED_API_KEY\", \"\").strip() else \"FRED_API_KEY missing or empty\")"'
bash -lic 'dc-web config --quiet'
if docker container inspect prumo-ingest >/dev/null 2>&1; then
    bash -lic 'dc-web stop prumo-ingest'
fi
bash -lic 'dc-web-up prumo'
docker exec prumo python -m ingest --help
docker exec prumo python -m ingest import-legacy --help
docker exec prumo python -m ingest run --help
docker exec prumo python -m ingest.scheduler --help
```

Keep the scheduler stopped throughout import and catch-up. Its single-instance lock does
not serialize separate CLI writers. Use only the original `indicators.csv` export, not a
DuckDB file, a reformatted spreadsheet or a newly invented fetch date. Set
`LEGACY_CSV` to the absolute path of that original file already on f0nix. The destination
check prevents accidental replacement of an earlier migration input.

```bash
: "${LEGACY_CSV:?Set LEGACY_CSV to the original indicators.csv absolute path on f0nix}"
[[ "$LEGACY_CSV" = /* ]]
test -f "$LEGACY_CSV"
docker exec prumo mkdir -p /data/migration
docker exec prumo test ! -e /data/migration/legacy-indicators.csv
docker cp "$LEGACY_CSV" prumo:/data/migration/legacy-indicators.csv
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    import-legacy /data/migration/legacy-indicators.csv
```

Review the import's actual imported/quarantined counts and status before proceeding. World
Bank continuity comes from the reviewed source-scoped legacy import/serving rules. Imported
rows retain `legacy-unverified` and their original retrieval dates. Do not enable global
legacy serving, convert units, change registry identities or bypass licence gates.

The initial E-REDES window is `[2026-04-01T00:00:00Z, actual UTC day start)`. The inspected
`run --help` defines `--to` as INCLUSIVE and requires it to be before today UTC. Consequently
use yesterday UTC for `--to`; passing today's date would fail rather than implement an
exclusive upper bound. Recheck help on the reviewed deployed revision and stop on an
interface mismatch. This command fetches real responses now; it never backdates retrieval.

```bash
END_EXCLUSIVE_UTC=$(date -u +%F)
LAST_INCLUDED_UTC=$(date -u -d "$END_EXCLUSIVE_UTC - 1 day" +%F)
printf 'E-REDES UTC window [2026-04-01, %s), CLI --to %s\n' \
    "$END_EXCLUSIVE_UTC" "$LAST_INCLUDED_UTC" > "$OP/eredes-window.txt"
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    run eredes --from 2026-04-01 --to "$LAST_INCLUDED_UTC"
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    status --json > "$OP/status-before-worker.json"
```

A nonzero import/catch-up result needs review before starting the worker. Keep the error
and healthy raw evidence; do not mark a failure as caught up. The controller may explicitly
accept an unresolved source exception and start retries, but must record its actual reason.
If the server's World Bank/E-REDES route fails, use the manual procedure linked below.

Verify the secret again immediately before starting the worker, then begin observation:

```bash
cd /home/joao/docker
sops exec-env secrets/web.enc.env \
    'python3 -c "import os; raise SystemExit(0 if os.environ.get(\"FRED_API_KEY\", \"\").strip() else \"FRED_API_KEY missing or empty\")"'
bash -lic 'dc-web-up prumo-ingest'
date -u +%Y-%m-%dT%H:%M:%SZ > "$OP/observation-start.txt"
docker exec prumo-ingest python -c \
    'import os; raise SystemExit(0 if os.environ.get("FRED_API_KEY", "").strip() else "FRED_API_KEY missing or empty")'
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    status --json > "$OP/status-start.json"
docker inspect prumo-ingest \
    --format 'running={{.State.Running}} restarts={{.RestartCount}} oom={{.State.OOMKilled}} healthcheck={{json .Config.Healthcheck}}' \
    > "$OP/worker-start.txt"
```

## Status, logs and data evidence

For the existing observation, set `OP=/home/joao/prumo-operations/task18-49a3602` in
the operator shell and retain its original observation start. Do not create a new start
timestamp merely to collect another snapshot.

Run status and read-only evidence commands in the web container; these remain available
when the worker is stopped. Status exit 0 means the report was produced, not that sources
are healthy. Review every dataset/group, including pending runs and inactive/blocked sources.

Since Task 23 (not in the deployed 49a3602 image until an authorized rebuild), `status` and
`lag` open the database strictly read-only (SQLite `mode=ro`): they never migrate and never
create a file. They exit 2 with a clear message when the file is missing or its schema is
older or newer than the code (the scheduler applies migrations; a report never does).
Read-only handles also use `readonly_shm=1`: `mode=ro` alone does not prevent writes to
SQLite's shared-memory index. A missing `-shm` alongside a `-wal` is left for the writer to
recover, even when the data directory is writable. Sidecar checks use the canonical database
path, including when the caller supplied a symlink. If a writer changes a database during an
immutable read, the report discards it and re-evaluates the read mode once. Every immutable
attempt is validated against the main-file stamp and the WAL; repeated races fail closed.
A quiet, checkpointed database remains readable without creating sidecars.
The text report shows, per source and in total, the active series that are stale, never
fetched and never verified (stale series ids listed, capped at 10); `last confirmed current`
next to the retained data's fetch date (stale is judged on the former, see
[methodology](methodology.md)); events in the last 24h, 7d and lifetime; and per dataset the
scheduler's persisted state: failure streak, next eligible time and any `running` marker
(in flight, or an attempt interrupted by a killed process), and the verifier channel of the
dataset's latest passed verification (`last verified via live|pinned-bundle`). A run
verified only against its own pinned bundle never counts as confirmed current: its series
stay stale with reason `pinned_bundle_only` until a live verification (Task 24). A
`pending-verification` run older than 24 h is marked `STALE` with its remedy and counted
in the `all sources` line (`pending verification over 24h N`, JSON
`totals.pending_stuck`); see "Interrupted runs" below. The scheduler logs one
`blocked` record per `verifiable: false` source (DGEG) at process start, not every pass.

```bash
bash -lic 'dc-web ps prumo prumo-ingest'
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw status
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw status --json
bash -lic 'dc-web logs --tail=200 prumo-ingest'
# Live log follow; Ctrl-C ends only the log viewer.
bash -lic 'dc-web logs -f --tail=100 prumo-ingest'
```

`status` judges retrieval time only. The read-only `lag` command (branch `pipeline-rebuild`
since Task 22; not in the deployed 49a3602 image until an authorized rebuild) judges DATA time:
`python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw lag` lists every ACTIVE series
whose newest fetched period lags today by more than the per-frequency allowance in
`ingest/data_lag.py` (A 3 years, S 3 halves, Q 4 quarters, M 6 months, D 30 days, PT15M 7 days)
and exits 1 if any does. Only periods of `verified` and `pending-verification` runs count:
a withdrawn or failed run (possibly a parser that invented a future period) never masks a
frozen series (Task 24). A hit means a possibly frozen or interrupted publisher series: confirm
with the publisher and record the disposition in `registry/unmapped-<source>.md`; never
deactivate on the lag alone.

Check SQLite read-only and sample successful response receipts since observation began.
This checks archived bytes/hash/size and original fetch timestamps, not publisher freshness
or permission to serve. A reused content hash may already have existed; the new receipt
still needs its real retrieval time. URLs/parameters and response bodies are not printed.
No successful receipts is an explicit failed evidence check, not a heartbeat success.

```bash
: "${OP:?Use the evidence directory created during bootstrap}"
docker exec -i -e SINCE_UTC="$(< "$OP/observation-start.txt")" prumo python - <<'PY'
import hashlib
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

with sqlite3.connect("file:/data/prumo.sqlite3?mode=ro&readonly_shm=1", uri=True) as db:
    assert db.execute("PRAGMA quick_check").fetchall() == [("ok",)]
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    rows = db.execute("""
        SELECT r.id, s.name, r.fetched_at, r.http_status, r.sha256, r.path, r.bytes
        FROM raw_fetch r JOIN source s ON s.id = r.source_id
        WHERE r.ok = 1 AND julianday(r.fetched_at) >= julianday(?)
        ORDER BY r.id DESC LIMIT 10
    """, (os.environ["SINCE_UTC"],)).fetchall()
    if not rows:
        raise SystemExit("No successful raw receipts since observation start; review status/logs")
    for ident, source, stamp, status, sha, filename, size in rows:
        path = Path(filename).resolve()
        assert path.is_relative_to(Path("/data/raw").resolve()), (ident, "raw path")
        body = path.read_bytes()
        assert len(body) == size, (ident, "byte count")
        assert hashlib.sha256(body).hexdigest() == sha == path.name, (ident, "sha256")
        fetched = datetime.fromisoformat(stamp)
        assert fetched.tzinfo is not None, (ident, "missing timezone")
        assert fetched <= datetime.now(timezone.utc) + timedelta(minutes=5), (ident, "future receipt")
        print(ident, source, stamp, status, size, path)
PY
curl -fsS http://100.118.19.6:8088/healthz
curl -fsS https://cae.joao.date/ | \
    python3 -c 'import sys; assert "Estatísticas oficiais" in sys.stdin.read()'
curl -fsS https://joao.date/dados/ | \
    python3 -c 'import sys; assert "Estatísticas oficiais" in sys.stdin.read()'
```

## Manual update with original response bundles

[Manual refresh](manual-refresh.md) is authoritative for capture, manifest validation,
source/indicator/window selection, return codes and original-file honesty. Production
imports target f0nix and the persistent container paths below. Do not duplicate the
capture procedure or treat an arbitrary browser download as an importable bundle.
No manual write is authorized merely by this runbook; keep the worker running during
the current observation unless the owner authorizes an interruption.

After following that document, place the complete, validated bundle on f0nix. Set
`BUNDLE_HOST` to its absolute directory and `BUNDLE_SOURCE` to `worldbank` or `eredes`.
For an indicator-scoped World Bank capture, set the same `INDICATOR`; for E-REDES set
`BUNDLE_FROM`/`BUNDLE_TO` to the original capture's inclusive day bounds. Do not substitute
today's dates for those bounds or its receipt timestamps. Run this while no other CLI writer
is active. This standalone block uses strict mode inside a subshell, leaving the
operator's parent shell open and its options unchanged. It stops on any failed
prerequisite and requires a successful stopped-state readback before preparing the
destination. A failed import returns nonzero without running status; collect diagnostics
separately and review the error before any restart. No failure triggers an automatic restart.

```bash
(
set -euo pipefail
: "${BUNDLE_HOST:?Set the absolute path of the complete captured bundle on f0nix}"
: "${BUNDLE_SOURCE:?Set worldbank or eredes}"
[[ "$BUNDLE_HOST" = /* ]]
test -f "$BUNDLE_HOST/manifest.json"
BUNDLE_NAME=$(basename -- "$BUNDLE_HOST")
BUNDLE_TARGET="/data/migration/bundles/$BUNDLE_NAME"
RUN_ARGS=(run "$BUNDLE_SOURCE" --bundle "$BUNDLE_TARGET")
case "$BUNDLE_SOURCE" in
    worldbank)
        if [[ -n "${INDICATOR:-}" ]]; then RUN_ARGS+=(--indicator "$INDICATOR"); fi
        ;;
    eredes)
        : "${BUNDLE_FROM:?Use the original captured first UTC day}"
        : "${BUNDLE_TO:?Use the original captured last UTC day, inclusive}"
        RUN_ARGS+=(--from "$BUNDLE_FROM" --to "$BUNDLE_TO")
        ;;
    *) printf '%s\n' 'Unsupported bundle source' >&2; exit 2 ;;
esac
bash -lic 'dc-web stop prumo-ingest'
WORKER_RUNNING=$(docker inspect prumo-ingest --format '{{.State.Running}}')
[[ "$WORKER_RUNNING" = false ]]
docker exec prumo mkdir -p /data/migration/bundles
docker exec prumo test ! -e "$BUNDLE_TARGET"
docker cp "$BUNDLE_HOST" "prumo:$BUNDLE_TARGET"
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw "${RUN_ARGS[@]}"
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw status --json
# Restart only after the actual result and retained/original dates have been reviewed.
)
```

The import's verifier reads the publisher over live HTTP from the container (Task 21): if
that route is down the import ends `failed-verification` with reason `verifier channel
unavailable` and nothing is served. Appending `--pinned-verifier` to `RUN_ARGS` verifies
against the bundle's own captured verifier responses instead; that is not audit-grade,
is recorded per verification as `verifier_channel='pinned-bundle'`, and needs an explicit
owner decision.

A stop interrupts continuity: record the stop and begin a new observation window after
resuming. Do not close the original window using interrupted uptime. On approval to
resume, re-run the silent SOPS key check above, then:

```bash
bash -lic 'dc-web-up prumo-ingest'
bash -lic 'dc-web logs --tail=100 prumo-ingest'
```

Then run `derive` (see "Derived layer"): a manual `run` does not trigger one, and the
scheduler derives only after its next verified attempt of that group.

```bash
docker exec prumo-ingest python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw derive
```

Recorded imports have `input_origin=recorded`; `started_at` is the import attempt time,
while `real_data_fetched_at` remains the original capture time. A passed recorded
verification does not make an old download fresh. Identical bytes or identical values
after a verified run can short-circuit without a new sample (a stale bundle is refused as
`blocked-stale` before its values are compared). A stale/partial/invalid bundle refusal
must remain visible and cannot justify replacing newer verified data.

## Withdrawing data, inactive series and interrupted runs

These are reviewed operator actions. None deletes stored rows; each leaves an event.

**Inactivate a series** (definition or unit defect found after the fact) by setting
`active: false` in `registry/core.yaml` through the normal reviewed registry change. From
migration 0011 the served view hides the series' verified *fetched* rows as well as its
legacy rows; reactivating it serves the retained history again. A series *removed* from the
registry is set inactive at the next registry sync (scheduler start or any CLI command that
syncs) and recorded as event `series_deactivated` with reason `absent_from_registry`.
Registry sync treats the given file as the whole registry, so never point a writing
command at a partial or scratch registry with the production `--db`.

**Withdraw one verified vintage** when a single fetched run is wrong (for example a
sampled verification that passed on a vintage later found defective) and the series
itself stays active. Identify the run from `status --json` or read-only SQL, then run the
command below with an explicit reason. Only a `verified`, non-legacy run can be withdrawn;
`withdrawn` is terminal, its rows are kept in `observation` but never served again, and the
reason is stored as event `withdrawal`. The view then falls back to the newest remaining
verified vintage for each period, if any. The database refuses any other path into
`withdrawn`, and from migration 0013 also an `INSERT OR REPLACE` that would recreate a
withdrawn run id (hand-written SQL included).

Withdraw the run that WROTE the rows. A run whose fetched bytes were identical to the
previous verified run, or whose parsed values (with status flags, release dates and
quarantine rows) were identical to its verified base run, is recorded `verified` with no
observations (the short-circuit for identical bytes or identical values; its result detail
names the base run) and vouches for that run; `withdraw` refuses such a run ("has no
observations"). Withdrawing the run that wrote the rows also withdraws, in the same
transaction and each with its own `withdrawal` event (`cascaded_from` = the run you named),
every later verified short-circuit of the same dataset chained onto it, up to the next run
that wrote rows or ended in another state. The command prints every run it withdrew. The
next fetch of the same bytes or values then follows a withdrawn run, so it is re-ingested as a new
run and served once verified, and `status` no longer counts the withdrawn short-circuits
as confirming the data current. To stop serving a series persistently, inactivate it.

```bash
: "${RUN_ID:?Set the dataset_run id that wrote the rows}"
: "${REASON:?Set the reviewed reason, e.g. a defect reference}"
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    withdraw "$RUN_ID" --reason "$REASON"
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw status --json
```

Then run `derive` (see "Derived layer"): derived values built on the withdrawn vintage are
no longer served, and the vintage served again gets derived values only from a new derive
run. Do not wait for status to ask for it: `DERIVED STALE` appears only when a key is left
with no served value at all, not when some of its periods lost theirs:

```bash
docker exec prumo-ingest python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw derive
```

**Interrupted runs.** A run whose process failed on our side (raw store I/O, a database
error such as `database is locked` after the 30 s busy timeout, or `docker stop`/SIGTERM)
ends `failed-operational` with event `operational_failure`, never `failed-fetch` or
`failed-validation`/`format_change`, which describe the publisher. A run left `running` by a
hard kill (OOM, SIGKILL) is closed the same way, with stage `orphaned`, when the scheduler
next starts. Since Task 24 that start-up sweep closes only a run the scheduler itself started
(its dataset has a scheduler attempt marker still `running` from no later than the run's
start; `swept_because: scheduler_attempt_interrupted`) or a run that started at least 6 h
earlier (`ORPHAN_MIN_AGE` in `ingest/db.py`; `swept_because: older_than_min_age`). A
younger manual run in the web container is left alone. Every state change the pipeline
makes out of `running` is a compare-and-set: if a run is closed while its process still
works on it, that process rolls back what it was writing, records
`operational_failure` with stage `closed_elsewhere` and reports the run's real state, so a
swept run is never resurrected. Stopping the worker before a manual import remains the rule.

**Interrupted verification.** A run stopped during verification (SIGTERM or a crash inside
`run_with_refetch`'s verify stage) stays `pending-verification`; nothing sweeps it. It is
never served, it still counts as held data for the recorded-replay stale guard, and
`status` marks it `STALE` after 24 h. The remedy is to verify that run with the verifier
registered for its source: `python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw
verify <run_id>` (in the web container, worker stopped as for any manual write). It ends
`verified` or `failed-verification`; the next scheduled run fetches afresh either way.

## Backoffice

`prumo-backoffice` is an operator view of the pipeline at
`http://100.118.19.6:8089` (Tailscale address of f0nix only; there is no Traefik or public
route and no login: Tailscale membership is the perimeter). It runs the same Dockerfile
under its own image tag `prumo-backoffice:latest`, so deploying it never retags or restarts
the worker's `prumo-ingest:latest`. Its include is `deploy/prumo-backoffice.yml`, installed
as `~/docker/stacks/web/compose/prumo-backoffice.yml`.

It is read-only except for one editor: `/editorial` chooses which series a public page shows
(see "Editorial composition" below). That is the container's only write path; every other
page reads.

Read-only guarantee, in three layers: the `/data` volume is mounted `:ro`; every read opens
the database through `ingest.db.read_db_readonly` (sqlite `mode=ro`, `query_only`, never
migrates or creates the file); every route is `GET`/`HEAD` except the six editorial POSTs. A
test (`tests/backoffice/test_app_overview.py`) fails when a non-GET route appears that is not
one of those six, so the write surface cannot grow unnoticed. A missing database or a schema
older/newer than the image's code gives an HTTP 503 page with the refusal text, like
`python -m ingest status`. `/healthz` always answers 200 while the app runs and reports
`"db": "ready"` or `"db": "unavailable"` (with `db_detail`) in its JSON body, so a database
hiccup never makes the container restart-loop.

| Page | Shows |
|---|---|
| `/` | Overview: the same totals and per-source table as `ingest status` |
| `/queue` | Derived review queue (rules below) |
| `/series` | Registry series with filters (source, theme, geography, frequency, active, text) and status, 100 per page |
| `/series/<id>` | Registry spec and licence, why an inactive series is inactive (verbatim lines of `registry/unmapped-*.md`), status, every stored period in any run state (served or not, licence-withheld sources included) with a period box, newest 200 served rows (legacy rows labelled unverified), raw fetches, verification items, quarantine; `?period=` adds that period's vintages |
| `/verification/item/<id>` | One stored verification item and a fresh offline replay of its archived evidence (match, mismatch, evidence missing, evidence corrupt, cannot replay, with the reason) |

Every page that uses the status report says when it was generated and how many seconds
ago: the report is cached for 30 s, so a page can be up to 30 s behind `ingest status`.

### Editorial composition

`GET /editorial` lists the code pages and says which list is in force; `GET /editorial/inicio`
edits one page: up/down/remove on the draft, a candidate list of eligible series with an
optional calculated companion, a publish block with the change against what is live and a
mandatory reason, discard, and reset.

What may appear on a page is one rule, applied twice: primary, active, licence allows
redistribution, at least one served fetched value, a title in the language the page renders,
and no other slot with the same title. `ingest/editorial_rules.py` holds it and both the
publish refusal and the render drop call it. A series that loses its licence after a publish
disappears from the page on the next request with one WARNING line naming the slug, the
series and the reason; the other cards render.

Writes go through `ingest.db.open_db_for_write` on `/data-w` (the same host directory as the
read-only `/data`), never through the read handle. That opener never migrates and refuses a
schema that differs from the image's code in either direction, so the editor answers 503
rather than writing into an unknown table shape. The handle also carries an SQLite authorizer
that refuses any write outside `editorial_page`, `editorial_slot` and `editorial_event`, so
"the backoffice edits the composition and nothing else" is enforced by the database, not by
review. Every mutation bumps `editorial_page.version`, so a form rendered in another tab gets
409 and writes nothing, and writes exactly one `editorial_event` row inside the same
transaction (publish stores the whole list in `detail_json`). A database the worker is writing
(the lock is held) answers 409 with "try again" after a short wait, never a 500.

Publishing shows the diff against what is live and the cards the home will draw, built by the
home's own card builder from the same reads; the reason is mandatory. The draft may hold a slot
that would not render any more; publish refuses and names every failing slot with its reason.

CSRF: there is no session, so every POST requires an `Origin` that is exactly the scheme,
host and port the request arrived on, and refuses `Sec-Fetch-Site: cross-site`. The `Host`
itself is allow-listed (400 otherwise); matching the `Origin` hostname alone would accept any
port on an allowed host, and `localhost`/`127.0.0.1` are in that list for the healthcheck.
Tailscale stays the perimeter; there is no login.

Rollback of a composition is the page itself: reset deletes both states and the page returns
to the list in code. The release that added the editor changes nothing a reader sees while
the tables are empty.

Installing the include (once, on f0nix) is what turns the editor on; before that the container
has no `/data-w` mount and `PRUMO_EDITORIAL_DB` is unset, so `/editorial` renders read-only
and every POST answers 503 while the rest of the backoffice works.

The order below matters twice. Migration 0018 must be applied before the backoffice starts,
or the editor refuses the database (503 with a "missing migrations" message) while every read
page keeps working. And both writers must be the same uid: SQLite writes require write access
to the database, its `-wal` and its `-shm`, and the worker used to run as root, leaving
`root:root` files uid 1000 cannot write. `dc-web-up prumo-ingest` now recreates it as
`1000:1000`, so the data directory is chowned once, with the worker stopped so it cannot
recreate a root-owned `-wal` underneath the new owner:

```bash
sudo docker stop prumo-ingest
sudo chown -R 1000:1000 /home/joao/docker/stacks/web/appdata/prumo
bash -lic 'dc-web-up prumo-ingest'
bash -lic 'dc-web-up prumo'
sudo cp ~/docker/stacks/web/images/prumo/deploy/prumo-backoffice.yml \
        ~/docker/stacks/web/compose/prumo-backoffice.yml
bash -lic 'dc-web-up prumo-backoffice'
```

The worker applies 0018 itself on that first start; the home still renders the list in code
because the tables are empty. Check it with `docker exec prumo-ingest ls -ln /data` (the
database, `-wal` and `-shm` must be `1000:1000`) and with one real POST from the editor: the
first publish is the only proof the write path is not a readonly 503.

### Editorial composition: installation record (2026-11-16)

DEPLOYED by owner authorization at 12:20-12:21 UTC on `main` `81c8eb9` (fast-forward from
`pipeline-rebuild`, pushed; the f0nix checkout `~/docker/stacks/web/images/prumo` was already
at the same commit). The order above was followed literally: all three containers stopped
(`prumo-ingest` exits 143), a cold copy of the database taken with every writer down
(`prumo-cold-20261116T122038Z.sqlite3`, 217 MB), the data directory chowned to `1000:1000`,
then `prumo-ingest` (12:21:04, applied 0018), `prumo` (12:21:31) and `prumo-backoffice`
(12:21:31). Images: `prumo` `c761fef64812`, `prumo-ingest` `d65a19e91a0f`,
`prumo-backoffice` `0fd546b4d87b`. Rollback point: `main` `7e563b2`, images `86215c61…`,
`34029ffc…`, `19023ee4…`, plus the two database copies above.

Post-deploy checks: `integrity_check` ok, 0 foreign-key violations, `observation` 542,822,
`quarantine` 34,219, `served_derived` 6,665 (23 keys, all `is_calculated = 1`) and `series`
1,791 all unchanged; `schema_migration` ends at `0018_editorial_composition`; the four
editorial tables exist and the page rendered from the code list is byte-identical to the
17,146-byte pre-deploy capture. `docker inspect` reports the worker as `1000:1000` and the
database, `-wal` and `-shm` as `1000:1000`. Restart count 0 on all three, no `error`,
`Traceback`, `MissingText` or `database unusable` in any log.

The write path was proved with one real publication, not a GET: two slots added
(`bportugal.credit_consumer.PT` with `derived.credit_consumer.PT.yoy_change_pct`, then
`bportugal.credit_housing.PT`), each answered 303; publish answered 303 and the home served
the composition (6,973 bytes, both cards, derived line included). `editorial_event` held the
three rows with versions 1, 2, 3 and publish's `detail_json` carrying both slots. Refusals
held on the live container: 403 with no `Origin`, 403 with `Origin: https://evil.example` and
`Sec-Fetch-Site: cross-site`, 404 for an unknown slug. `reset` (version 4) then deleted both
states, logged `reset_to_code`, and the home came back byte-identical to the 17,146-byte
pre-deploy capture: **the production site is serving the code list, not the trial
composition.** Every link on the home (21), the series CSV, the calculated page and its CSV,
`cae.joao.date`, `joao.date/dados` and the CSP header were re-checked after the deploy.

A post-deploy defect was then found by reading the rendered page, not by a status code:
`/editorial/inicio` carried "The writable mount is not configured" while the POSTs next to it
were writing. `editorial_page.html` tests `available`, and `editor_page()` never passed it, so
Jinja's default `Undefined` made the flag falsy on every request. Fixed in `1a34ccb`
(`available=editorial.available()`), with one test for each direction: the banner is absent
when the writable path is configured and present when it is not, and the first of the two
fails without the fix. Only the backoffice image was rebuilt and only that container recreated
(12:44:35); web and worker untouched. Suite `2220 passed, 7 deselected`, `ruff` clean.

One operational note from the same window: `prumo-ingest` restarted once at 12:36:07, exactly
15 minutes after its first start, with exit code **135 (SIGBUS)** and `OOMKilled=false`. The
host has 83 GB free, no I/O errors, the container's memory peaked at 61.5 MB against a 512 MB
limit, and the scheduler had nothing due in that pass (every group was verified earlier in the
day; 112 KB read from disk). Three back-to-back ticks against a copy of the database ran to
completion without a crash, so it is not reproducible on demand. `restart: unless-stopped`
brought it back in 0.15 s and the scheduler state is unchanged. Treat it as unexplained and
watch it: if it recurs, capture the tick that kills it before assuming a cause. It does not
affect data (counts, integrity and FK checks unchanged after the restart), but it does break
the continuity of the Task 18 24-hour worker observation, which has to restart its clock.

### Review queue rules

Derived on every `/queue` request from the last 7 days; nothing is stored. Event kinds are
the ones the pipeline emits (`ingest/pipeline.py`, `verify.py`, `db.py`):

| Item | Severity | From |
|---|---|---|
| `verification_failed`, `verification_escalated` | high | one per event |
| `format_change` | high | one per event, including the per-series `no_valid_observations` event written inside an otherwise successful run (that series stopped receiving data) |
| `stale_refusal` | high | one per event (a recorded replay older than the verified data held) |
| `stuck_pending` | high | the status report's pending runs older than 24 h (same as the overview's total) |
| `operational_failure` | medium | one per event (orphan sweep, write lock, interrupted run) |
| `verifier_outage` | medium | one per event whose run was not escalated (an escalated run already has a high item) |
| `fetch_failure_streak` | medium | a dataset whose last 2+ finished runs are all `failed-fetch` (any origin, CLI included) |
| `scheduler_streak` | medium | a dataset whose scheduler `failure_streak` is 2+ (any non-verified outcome) |
| `stale_series`, `lagging_series` | medium | status report / `ingest lag` |
| `revision_burst` | info | a run with 100+ revision events (counted in SQL) |
| `new_period_gap` | info | a `new_periods` event whose added periods are not contiguous (already held in between, or missing); PT15M series are not judged |
| `quarantine` | info | quarantined rows per source and reason |
| `blocked_source` | info | licence-withheld or not-verifiable sources |

Not queued: `refetch`, `withdrawal` and `series_deactivated` (records of actions already
taken; the overview's per-source event counts show them). Reads are bounded: revisions,
`new_periods` and quarantine are aggregated in SQL and each per-event kind is read with a
200-row limit (at most 1,900 event rows per request); a read that hits its limit is named on
the page.

### Container hardening

- Own plain bridge network `prumo_backoffice`, not `t2_proxy`: no other container and no
  Traefik can reach port 8080. It is not `internal: true`, because Docker publishes no ports
  for a container attached only to internal networks.
- No `resolv.conf` mount: the app makes no outbound call (replay re-reads archived
  evidence offline).
- `read_only: true` root filesystem with a `tmpfs` on `/tmp`, `cap_drop: [ALL]`,
  `no-new-privileges`.
- It runs as `user: "1000:1000"`. `RawStore` writes raw evidence mode 0644 (public-source
  bytes; it used to be 0600 via `tempfile.mkstemp`). A worker image older than that change
  still writes 0600 root files that the replay page cannot read: run
  `docker exec prumo-ingest chmod -R a+rX /data/raw` (no restart) after deploying the
  backoffice and again until the worker image is rebuilt and restarted.
- Host header allow-list (DNS-rebinding guard): `PRUMO_BACKOFFICE_ALLOWED_HOSTS`,
  comma-separated, default `100.118.19.6,localhost,127.0.0.1`. Add the MagicDNS name there
  if you browse by name. Every response carries `Content-Security-Policy: default-src 'none';
  style-src 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'` (the pages use no
  JavaScript).
- Before the first deploy, confirm f0nix's Traefik runs with `exposedByDefault=false` (the
  backoffice has no labels; this only matters if it ever joins the proxy network again).

### Boot order and the Tailscale bind

The port is published on `100.118.19.6` only. If `tailscaled` has not brought that address
up when dockerd starts the container at boot, Docker fails to bind ("cannot assign requested
address") and the container does not start. `restart: unless-stopped` does not help here:
Docker's documentation states that "a restart policy only takes effect after a container
starts successfully", and this one never started, so after a reboot check it and start it by hand if needed:

```bash
docker inspect prumo-backoffice --format 'running={{.State.Running}} error={{.State.Error}}'
bash -lic "dc-web-up prumo-backoffice"
```

A durable fix is host-level (order `docker.service` after `tailscaled.service` with a
systemd drop-in); it is not part of this repository.

Deploy (controller, owner-authorized; never restart `prumo-ingest` for it):

```bash
bash -lic "dc-web-up prumo-backoffice"
curl -fsS http://100.118.19.6:8089/healthz
docker inspect prumo-ingest --format 'started={{.State.StartedAt}}'
```

After deploy, while the worker is mid-run, confirm that the read-only mount creates nothing
and the DB reads as ready (the review's one unobserved case: a live writer on a real EROFS
mount):

```bash
ls -la ~/docker/stacks/web/appdata/prumo/
curl -fsS http://100.118.19.6:8089/healthz
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: evil.example' http://100.118.19.6:8089/
```

The last command must print `400`.

## Derived layer

Derived layer v1 (project 3; migration 0014, status schema v4) computes a closed set of
calculated series from verified served data only. Definitions live in the top-level
`derived:` list of `registry/core.yaml` (kept byte-identical in `core.proposed.yaml`); the
method is in [methodology](methodology.md#derived-values).

What is computed: for each ACTIVE derived key, `period_change`, `period_change_pct`,
`yoy_change`, `yoy_change_pct` or `rebase_100` over ONE base series, using only that base's
`kind='fetched'` rows currently in `served_observation` (never legacy rows). Each run
recomputes 100% of its new values independently (`ingest/derive_verify.py`, fractions) and
is `verified` only when every value matches; a `failed` run serves nothing. The starter set
is 23 keys over 20 PT bases (industrial production, trade, credit/deposits, demography, GDP
per capita as `yoy_change_pct`; unemployment rate and 10-year yield as `period_change` /
`yoy_change` in `p.p.`; consumer confidence as `period_change` in `balance`; unit labour
cost rebased to 2015 = 100).

Manual run, inside the worker container (it holds the writable DB):

```bash
docker exec prumo-ingest python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw derive
docker exec prumo-ingest python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    derive --series derived.unemployment_monthly.PT.period_change   # repeatable
```

`derive` validates the registry's `derived:` list and every `--series` key before opening
the DB, never creates a DB, syncs the derived registry (a key removed from YAML becomes
inactive, never deleted) and prints
`derive run N: <state>; S series, W new values, K skipped, M mismatches[, E compute errors]`.
`nothing to derive` means no active key was in scope. A second run with unchanged inputs
writes 0 new values.

Scheduler trigger: after a group's attempt is recorded `verified`, the scheduler runs one
derive over the active keys whose base is in that group and logs a JSON line
`{"event": "derive", "group": ..., "run_id", "state", "n_written", "n_mismatch"}` (or
`"state": "error"` with the exception text). A derive failure never changes the base
attempt, its retry/streak state or the `--once` exit code. `derive` exits 2 with one
`derive refused: ...` line on a refused registry edit (see Known limitations) or a
database error such as `database is locked`.

Serving rule (`served_derived`): per (derived key, period) only the NEWEST version - the
highest-id `match` row of a `verified` derive run - is a candidate, and it is served only
while EVERY input observation id it used is still in `served_observation` as `fetched`.
Older versions are never served again. A new verified base vintage therefore hides the
derived rows built from the old vintage at once; the next derive (scheduler, or manual)
adds new row versions and keeps the old ones in `derived_observation`. Withdrawing a base
run, making a base inactive or withholding its source licence unserves its derived rows.
After a base withdrawal the older vintage is served again, but its periods serve NO derived
value until `python -m ingest derive` runs (it writes a new version on the older inputs;
history keeps every version). Status shows a key as `DERIVED STALE` meanwhile only when the
withdrawal left it with no served value at all; a key that lost some periods still reads
`current`, so run `derive` after every withdrawal without waiting for status. A newer
pending, mismatched or failed-run row never hides an older served one.

Events (`derived_event`, migration 0014): `zero_denominator` (no row for that period),
`missing_base_period` (`rebase_100` base period not served: no rows for that key),
`mismatch` (independent recomputation disagrees: run `failed`) and `compute_error` (a
formula raised: run `failed`). Refusals are recorded once per (period, reason, inputs).

Status: `python -m ingest status` (schema v4) prints one line

```text
derived: A active series; V served values; stale S / never computed N; last run R (state, started_at); failed runs 7d F
```

plus `DERIVED STALE <keys>` (capped at 10) when any. A key is `stale` when its base's
newest served `fetched_at` is later than the start of the latest verified derive run that
covered it, or when its base has served fetched data but the key serves 0 values. The
second case has two causes. After a base withdrawal it clears when `derive` runs. A key
that can produce no value at all stays `stale` however often `derive` runs: a `rebase_100`
whose base period is not served, a year-on-year key whose base has under a year of periods,
or a key whose every period has a zero denominator. The reason is in `derived_event` for
that key (`missing_base_period`, `zero_denominator`); the backoffice does not list events
yet. A key is `never computed` when its base has
served fetched data but no verified run covered it; a base with nothing served counts as
neither. `/derived` reuses its list for 30 s (the status cache TTL) and says when it was
generated.

Backoffice (read-only, same rules as above): `/derived` lists every derived series (pt title,
formula, base, unit, active, state, last covering run); `/derived/<key>` shows the
definition, served values with their input observations, every stored version (row state,
run state, served or not) and the newest derived runs. Derived series carry a "calculado"
badge.

Known limitations and rules (v1):

- One poison base value fails the WHOLE derive run of its scope (every key in that run is
  served from no row of that run). In the CLI, isolate it with `derive --series KEY` for the
  healthy keys; the scheduler has no workaround (its scope is the group's bases) until the
  base value is corrected or the derived key deactivated.
- The "already computed" skip compares input observation ids, not formula code. After a fix
  to a formula's code, existing rows would NOT be recomputed: add a NEW derived key (and
  deactivate the old one). The `formula`, `base` and `params` of an existing key are
  immutable (0014 rows are never relabelled); a new definition needs a new key.
- A registry edit that changes the `formula`, `base` or `params` of an existing key is
  refused: the scheduler logs one `{"event": "derive", "group": null, "state": "error"}`
  record at start and keeps refreshing base data, deriving with the definitions already
  stored in the DB (a NEW key added in the same edit is not synced either until the edit is
  reverted); `python -m ingest derive` prints `derive refused: ...` and exits 2.
- Percent formulas keep the denominator's sign and are not meaningful on series that cross
  zero. The starter set forbids `%` formulas on `%`, `balance` and `% GDP` bases (a test
  enforces it); rate series use differences in `p.p.`.
- Migration `0014_derived_layer.sql` must never be edited after deploy: migrations are
  tracked by name, not checksum, so an edit would silently not apply on an existing DB (it
  was edited in place before its first deploy, which is safe only because no DB had run it).
- Deploy order: one image builds all three containers, and old code refuses a 0014 database
  ("schema is newer than this code", exit 2 / HTTP 503). In ONE deploy, in this order:
  1. `bash -lic "dc-web-up prumo-ingest"` (the worker; it migrates to 0014);
  2. `bash -lic "dc-web-up prumo"` (the web container, where the runbook runs `status`,
     `withdraw` and manual imports);
  3. `bash -lic "dc-web-up prumo-backoffice"`.
  Between steps the not-yet-rebuilt containers refuse the newer schema (short window,
  expected). The running worker image contains no derived code until it is rebuilt.
- Read cost: per-key reads (`/derived/<key>`) search by key and stay well under 1 s; the
  whole-view reads (status derived line, `/derived`) cost about 1.7 s at ~50 daily base
  vintages (production copy, 2026-11-15), most of it in the 0011 `served_observation`
  lookup, which grows with the number of vintages of a period. Since the identical-values
  short-circuit (vintage dedupe, Decision 1) a daily fetch whose values are unchanged stores
  nothing; when any INE value changes a complete INE vintage is still stored, because INE is
  one dataset. A run in which any series has no valid observations is always stored, so
  its `format_change` event is kept (a dataset with a permanently empty series is never
  deduplicated). Unchanged days get no independent re-verification of their own (as for
  identical bytes). Duplicate vintages stored before the rule are kept.
- The `docker exec prumo-ingest chmod -R a+rX /data/raw` note under Container hardening
  still applies until the worker image that writes 0644 evidence is running.

After deploy, in this order:

- in `prumo` (the web container; proves step 2 ran):
  `docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw status`
  shows the `derived:` line;
- in `prumo-ingest` (the worker; first derive without waiting for the scheduler):
  `docker exec prumo-ingest python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw derive`;
- from the host: `curl -s -o /dev/null -w '%{http_code}\n' http://100.118.19.6:8089/derived`
  prints `200` (the backoffice, `prumo-backoffice`);
- `served_derived` has rows only with `is_calculated = 1` (read-only, in `prumo`; prints
  `(N, 1, 1)` with N > 0):

```bash
docker exec prumo python -c 'import sqlite3; c = sqlite3.connect("file:/data/prumo.sqlite3?mode=ro", uri=True); print(c.execute("SELECT COUNT(*), MIN(is_calculated), MAX(is_calculated) FROM served_derived").fetchone())'
```

## Vintage dedupe, caveats and language-neutral data (0015-0017)

Deployed 2026-11-15 19:14 UTC from `main` 761590e (image rebuilt for all three containers). This
section stays as the record of what the migrations do; the deploy steps below are history.

- `0015_observation_run_index`: index `observation_run` on `observation(dataset_run_id,
  series_id)`. The per-run reads of the identical-content short-circuit (`Db.run_content`,
  `Db.content_base_run`) stop scanning `observation`.
- `0016_language_neutral_derived`: `derived_series` loses `label` and `formula_label_pt`;
  `unit` becomes a closed code (`pct`, `pp`, `balance`, `index_2015_100`) and `served_derived`
  exposes codes plus the publisher's attribution only. Reader text lives in the `presentation/`
  package (`pt`, `en`); a missing catalogue key raises instead of rendering a raw code.
- `0017_derived_caveats`: `derived_series.caveats_json` (default `[]`) and a `caveats` column
  on `served_derived`. Nine keys carry one: `sa_base` on the six seasonally-adjusted IPI keys,
  `stock_base` on the three credit/deposit keys. A caveat says a calculated rate may differ
  from the publisher's own headline rate for a stated reason; the data layer stores codes, and
  the sentence comes from `presentation/`.

Identical-content short-circuit (vintage dedupe): when a dataset's new content equals the
stored content of its base run, the run ends `verified` with 0 observations and 0 quarantine
rows and the CLI prints `values identical to verified run N: nothing stored`. No new
verification is invented: status counts the series as current through its verified
short-circuit chain. A run of a dataset with an empty series, a superseded base, a base
verified only from its own pinned bundle, or a base in any non-verified state is stored in
full. Vintages stored before this rule are kept; compacting them is a later, optional
decision. Because INE is one dataset, any changed INE value still stores its complete vintage.

Deploy, in ONE run and only with owner authorization (`old code refuses a newer schema`; the
backoffice reads `formula_label_pt`, which 0016 removes, so it must be rebuilt in the same run):

1. `bash -lic "dc-web-up prumo-ingest"` (worker; applies 0015-0017);
2. `bash -lic "dc-web-up prumo"`;
3. `bash -lic "dc-web-up prumo-backoffice"`.

After deploy: `status` prints the same derived line as before (23 of the 23 keys stay
`current`); a manual `derive` writes 0 new values; `/derived` answers 200 and a caveated key
shows its sentence; `served_derived` still holds 6,665 rows for 23 keys.

Measured on a copy of the production database at 0014 (2026-11-15, 158.7 MB): migrations
0015-0017 applied in 2.4 s, `integrity_check` ok, 0 foreign-key violations, every derived row
and event unchanged (23 series, 6,665 observations, 6,665 served, 0 events), `observation`
497,338 and `quarantine` 34,157 unchanged, file 176.9 MB afterwards (the new index). Read cost
for the daily INE vintage (12,034 rows): `run_content` 40.9 ms against 88.1 ms without the
index, `content_base_run` 26-32 ms against 214-228 ms. Whole-view and per-key derived reads
were unchanged within noise (0.9 ms list, 9.3 -> 9.6 ms for 500 detail rows).

## Public site (project 4)

The `prumo` container serves the public statistics site from the same image and the same SQLite
file as before; the maintenance page is gone. No new service, no migration, no write path: every
request opens the database through `read_db_readonly` and the app never migrates it.

Deployed 2026-11-15: `main` `4fd3de8`, web container recreated at 22:39 UTC and again at 22:58 UTC
(after a post-deploy fix: a calculated chart appended its unit a second time), `prumo-ingest` and
`prumo-backoffice` not restarted. Pre-deploy rollback point: `main` `6f47894`, image `1a547dae…`.

- Routes: `/` (curated figures), `/temas/{economy,demography,energy}` (catalogue with filters and
  pagination), `/series/{id}` (chart, table, provenance, revisions, cross-checks), `/calculadas/{key}`,
  `/pesquisa?q=`, `/fontes`, `/metodologia`, `/series/{id}.csv`, `/calculadas/{key}.csv`, `/healthz`.
- Two public URLs: `cae.joao.date` at root and `joao.date/dados` behind Traefik `StripPrefix`; every
  link and asset URL is built from `X-Forwarded-Prefix`, and responses carry
  `Vary: X-Forwarded-Prefix`.
- Reader text comes from `presentation/catalog/pt.py`: no series id, derived key, unit or flag code
  reaches a page or an export. A missing catalogue key, or a view this code expects but the database
  lacks, answers the 503 page and logs `MissingText`/`database unusable` at ERROR in `docker logs
  prumo`. Withheld sources (REN, FRED, OECD, DGEG) are named on `/fontes` with a reader note and are
  never queried for a value.
- The catalogue and home counts are cached in-process for 30 s; series pages are computed per request
  (measured on a copy of production: home 87-91 ms, 15-minute series 186 ms, `/fontes` 27 ms,
  catalogue under 60 ms).

Deploy, code only, with owner authorization:

```bash
bash -lic 'dc-web-up prumo'
```

This rebuilds the shared image and recreates only the web container. No schema change is involved,
so `prumo-ingest` and `prumo-backoffice` are not restarted; the public read methods added to
`ingest/db.py` are additive and the backoffice's own reads are untouched.

After deploy, all of these must hold:

```bash
curl -fsS https://cae.joao.date/healthz
curl -fsS https://cae.joao.date/ | grep -q 'Estatísticas oficiais'
curl -fsS https://cae.joao.date/fontes | grep -c 'withheld-note'   # 4
curl -fsS https://cae.joao.date/series/ine.hicp_yoy.PT | grep -q 'IHPC'
curl -fsSI https://cae.joao.date/ | grep -i 'content-security-policy'
curl -fsS https://joao.date/dados/ | grep -q '/dados/static/css/prumo.css'
docker logs prumo --since 5m 2>&1 | grep -E 'MissingText|database unusable' || true
```

Rollback: deploy the previous commit on `main` again (`git checkout <prev> && bash -lic
'dc-web-up prumo'`). The database is not touched by this release, so there is no data step; the
previous image is the maintenance page.

### Two-series comparisons: installation record (2026-11-16)

DEPLOYED by owner authorization at 15:33 UTC on `main` `f0233bf` (fast-forward from
`pipeline-rebuild`, pushed; the f0nix checkout was fast-forwarded to the same commit). Code only:
`deploy/` is byte-identical to the installed `compose/prumo.yml` and `compose/prumo-ingest.yml`
includes, no migration, no write path, so `bash -lic 'dc-web-up prumo'` rebuilt the shared image
and recreated only `prumo` (image `ff71f042…`, `StartedAt` 2026-11-16T15:33:49Z, restart count 0).
`prumo-ingest` (`StartedAt` 12:36:07Z) and `prumo-backoffice` (`StartedAt` 12:44:35Z) were not
restarted. Pre-deploy rollback point: `main` `46d8d2e`, image `c761fef6…`; the database is
untouched, so the rollback is the previous commit and the same command. Infra pointer: `7520155`.

Gate before the rebuild: full suite on the merged tree `2250 passed, 7 deselected in 955.65 s`,
`ruff check app/ ingest/` clean, on top of the two review rounds already closed on the branch.

Post-deploy checks that held:

```bash
curl -fsS https://cae.joao.date/healthz                                     # 200
curl -fsS https://cae.joao.date/ | grep -q 'Estatísticas oficiais'
curl -fsS https://cae.joao.date/comparar | grep -c 'períodos comuns'        # 3 pairs listed
curl -fsS https://cae.joao.date/comparar/credito-e-taxa | grep -c '<circle' # 788 = 2*393 + 2 markers
curl -fsSI https://cae.joao.date/comparar | grep -i 'content-security-policy'
curl -fsS https://joao.date/dados/comparar | grep -q '/dados/'
curl -s -o /dev/null -w '%{http_code}\n' https://cae.joao.date/comparar/nao-existe  # 404
```

Measured after the rebuild: `/comparar` 3,807 bytes at the root prefix and 3,921 at `/dados`;
the three pair pages 200 with 344 / 359 / 393 plotted points and as many table rows; series ids
appear only inside the two `href`s to the series pages; no `<script>`, no `style=`, no
`must confirm|pending|UNVERIFIED`; CSP unchanged at `default-src 'none'`; each side carries its
own provenance for the last **common** period (one value sampled, the other explicitly not);
`docker logs prumo` shows no `error`, `Traceback` or `MissingText`.

### Typography cleanup: installation record (2026-11-16)

The owner authorized the repository-wide U+2014 removal, commit/push/merge and web-only deploy.
Code release `9001113e677aee3f707fd28041240f06c230b632` was fast-forwarded to main, pushed,
and installed on f0nix through `bash -lic 'dc-web-up prumo'`. Only `prumo` was recreated:
`StartedAt` `2026-11-16T19:31:02.759397671Z`, image
`a46672e3d205946c96509dd6441a7897313f79eabc21492004e272038c0eee3e`, healthy, restart count 0.
Worker and backoffice kept exactly the same container ids, image ids, StartedAt and restart counts
as before (worker 1, backoffice 0); no schema migration, registry sync, manual import or data edit ran.

The cleanup changes authored strings, not original source receipts. Stored source attribution and
licence strings can still contain U+2014 because the worker was intentionally not replaced;
`presentation.source_text` normalizes those fields only at public display/export boundaries.
Observation tokens, source records, URLs and publisher bytes remain unchanged. The original
receipt with an encoded publisher dash is hash-pinned by `tests/test_typography.py`; the DGEG
raw receipts and the extracted publisher bodies are unchanged, with derived-preamble hashes
updated in their manifest. The punctuation-only change to historical migration 0014 does not
rerun that migration; deployed schema remains 0018.

Release gates: independent cleanup review and scoped re-review approved; six old-metadata route
regressions failed before and passed after; full offline suite `2274 passed, 7 deselected,
3 warnings in 964.91 s`; ruff clean. GitHub CI for the released code passed:
https://github.com/joaompfp/prumo/actions/runs/43938228195 .
Desktop/mobile methodology screenshots against the production copy were checked before release.

Post-deploy: 42 HTTP 200 checks across `cae.joao.date` and `joao.date/dados`, including methodology,
sources, themes, comparisons, primary and derived detail, both CSV export types, CSS and health.
Every response is free of literal and HTML-encoded U+2014; the unknown comparison stays 404 on both.
CSP and prefixed CSS links are preserved. Browser DOM: `Metodologia - Prumo`, zero U+2014.
The web log has no error-class line. The before/after SHA-256 of the SQLite schema is
`026ff19e19052fa239024ab758e7a2247af39909eecf2b268574ce807b1b6ccf`, and the complete source
metadata hash is `1d74e8c63dc8422573830456b27596842518be3e911ca62f5c943027639df814`, unchanged.
This is not a claim that all observation counts stay fixed while the scheduler runs.

Rollback: code `3cb9d51`, previous web image
`ff71f0425fdde43ba1441fe4b2f437bec6ceca09b0f846a7dc26fdf8a9b8a66c`, with the same code-only
web deploy; no database rollback is needed. Later documentation-only commits advance the checkout
without rebuilding the already-verified image. ECharts remains a design/probe, not an installed feature.

## Rollback

The safe ingestion rollback is to stop the worker and retain the new maintenance web app,
SQLite, original CSV and all raw evidence. It does not roll schema backward, delete scheduler
state, restore DuckDB, run an old collector or change serving/registry flags. A stopped
worker means ingestion is unavailable; record the stop and do not claim a healthy service.

```bash
: "${OP:?Use the evidence directory created during bootstrap}"
bash -lic 'dc-web stop prumo-ingest'
date -u +%Y-%m-%dT%H:%M:%SZ > "$OP/worker-stopped.txt"
docker inspect prumo-ingest --format 'running={{.State.Running}}' \
    > "$OP/worker-stopped-state.txt"
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    status --json > "$OP/status-stopped.json"
curl -fsS http://100.118.19.6:8088/healthz
curl -fsS https://cae.joao.date/ | \
    python3 -c 'import sys; assert "Estatísticas oficiais" in sys.stdin.read()'
```

If the web image itself needs reversal, the controller must first review the recorded
`code-before.txt`/`web-image-before.txt` and schema compatibility. Do not automatically run
the historical entrypoint against the new SQLite volume. Use a separately reviewed
maintenance-compatible image/config rollback; no destructive data downgrade is provided.
After a reviewed fix, resume with the secret check and `dc-web-up prumo-ingest`, then start
a new acceptance window if continuity was interrupted.

## 24-hour acceptance

Leave the observation open until actual elapsed UTC time is at least 24 hours. Keep logs
before rotation (json-file is bounded to 10m x 3); absence of older logs is missing evidence.
Run at start, during the window and at its end, retaining per-group exceptions and the
actual source errors without credentials. Use the same `OP` directory throughout.

```bash
: "${OP:?Use the evidence directory created during bootstrap}"
SINCE_UTC=$(< "$OP/observation-start.txt")
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
docker logs --timestamps --since "$SINCE_UTC" prumo-ingest \
    > "$OP/worker-$STAMP.log" 2>&1
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    status --json > "$OP/status-$STAMP.json"
docker inspect prumo-ingest \
    --format 'running={{.State.Running}} restarts={{.RestartCount}} oom={{.State.OOMKilled}} healthcheck={{json .Config.Healthcheck}}' \
    > "$OP/worker-$STAMP.txt"
python3 - "$OP/observation-start.txt" <<'PY'
import sys
from datetime import datetime, timezone
from pathlib import Path

start = datetime.fromisoformat(Path(sys.argv[1]).read_text().strip())
now = datetime.now(timezone.utc)
print("observation_start_utc", start.isoformat(), "review_utc", now.isoformat())
if (now - start).total_seconds() < 86400:
    raise SystemExit("24-hour observation still open")
PY
```

The review must establish:

- The worker stayed running without unexplained restarts/OOM or overlapping writers.
  Review actual JSON group-attempt logs and persisted retry state for due attempts;
  sleeping between attempts is not itself failure. Do not infer success from process uptime.
- Compare start/end status for every active series and dataset, not just the most recent
  source-level attempt. World Bank indicators are independent groups: healthy siblings
  cannot hide a failed indicator. List `failed-fetch`, validation/verification failures,
  pending/stale runs, never-fetched and stale series with their actual reasons.
- Re-run the read-only SQLite/raw checks and public maintenance checks. Confirm the initial
  E-REDES window, real response receipts and stored UTC periods, without conversion or
  fabricated history. The raw sample is evidence for those receipts, not all groups.
- Record DGEG's inactive/unverifiable block and unconfirmed reuse grant. REN, FRED and OECD
  remain withheld by `redistribution_ok=false` even when internally verified. FRED API
  access is distinct from IMF permission; OECD dataset-level rights remain unconfirmed.
  Consult `registry/licences-todo.md` on the installed revision; do not bypass these gates.
- For World Bank route failures, record the actual affected indicators, retry results and
  dated `legacy-unverified` continuity. For recorded updates, compare original capture
  times with `real_data_fetched_at`, not import time. Other network/source failures must
  also remain explicit; never report hypothetical success for a route not exercised.

Only the controller can close the observation using real start/end evidence and reviewed
exceptions. Do not claim all core groups are fresh or available while known failures,
legal withholding, stale recorded data or missing verification remain.
