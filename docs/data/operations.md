# Prumo image and ingestion operations

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
contract. The currently inspected ingestion CLI reads the older `PRUMO_DB` variable as
its DB override. All operator CLI commands below therefore pass `--db` and `--raw-dir`
explicitly, before the subcommand. Do not rely on that older variable or change CLI code
as part of an image deployment.

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

```bash
bash -lic 'dc-web ps prumo prumo-ingest'
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw status
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw status --json
bash -lic 'dc-web logs --tail=200 prumo-ingest'
# Live log follow; Ctrl-C ends only the log viewer.
bash -lic 'dc-web logs -f --tail=100 prumo-ingest'
```

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

with sqlite3.connect("file:/data/prumo.sqlite3?mode=ro", uri=True) as db:
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
    python3 -c 'import sys; assert "Em manutenção" in sys.stdin.read()'
curl -fsS https://joao.date/dados | \
    python3 -c 'import sys; assert "Em manutenção" in sys.stdin.read()'
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

A stop interrupts continuity: record the stop and begin a new observation window after
resuming. Do not close the original window using interrupted uptime. On approval to
resume, re-run the silent SOPS key check above, then:

```bash
bash -lic 'dc-web-up prumo-ingest'
bash -lic 'dc-web logs --tail=100 prumo-ingest'
```

Recorded imports have `input_origin=recorded`; `started_at` is the import attempt time,
while `real_data_fetched_at` remains the original capture time. A passed recorded
verification does not make an old download fresh. Identical bytes after a verified run
can short-circuit without a new sample. A stale/partial/invalid bundle refusal
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
`withdrawn` (hand-written SQL included). Withdrawal removes that one vintage only: if the
publisher still returns the same values, the next scheduled run re-ingests them as a new
run and serves them once verified. To stop serving a series persistently, inactivate it.

```bash
: "${RUN_ID:?Set the dataset_run id to withdraw}"
: "${REASON:?Set the reviewed reason, e.g. a defect reference}"
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw \
    withdraw "$RUN_ID" --reason "$REASON"
docker exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw status --json
```

**Interrupted runs.** A run whose process failed on our side (raw store I/O, a database
error such as `database is locked` after the 30 s busy timeout, or `docker stop`/SIGTERM)
ends `failed-operational` with event `operational_failure`, never `failed-fetch` or
`failed-validation`/`format_change`, which describe the publisher. A run left `running` by a
hard kill (OOM, SIGKILL) is closed the same way, with stage `orphaned`, when the scheduler
next starts. That start-up sweep assumes no manual CLI writer is running at the same time,
which this runbook already requires (stop the worker before a manual import).

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
    python3 -c 'import sys; assert "Em manutenção" in sys.stdin.read()'
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
