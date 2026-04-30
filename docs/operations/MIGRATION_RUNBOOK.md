# Prumo Migration Runbook (Jarbas)

Purpose: safely adopt the new Prumo setup (first-run `/data` bootstrap + compose layering) on the current `stacks/web` server with clear go/no-go gates and fast rollback.

> Scope: operational procedure only. Do not change app code or compose logic while executing this runbook.

---

## 0) Quick go/no-go checklist (operator summary)

- [ ] Confirm current service is healthy and reachable before touching anything.
- [ ] Create timestamped backup of `stacks/web/appdata/prumo` (including DB files).
- [ ] Validate effective compose config with stack entrypoint before cutover.
- [ ] Rehearse with `docker compose ... config`/image inspect checks (no deploy yet).
- [ ] During cutover, monitor startup logs and `/healthz` until healthy.
- [ ] Validate key routes/endpoints after cutover.
- [ ] If any blocker fails at decision gates below, execute rollback immediately.

---

## 1) Preconditions and pre-checks

Run from `/home/joao/docker`.

1. Confirm baseline status:

```bash
source /home/joao/.bash_aliases

dc-jarbas-ps prumo
dc-jarbas-logs prumo
```

2. Confirm current compose resolves cleanly via the current stack entrypoint:

```bash
# Preferred stack entrypoint command
source /home/joao/.bash_aliases

dc-jarbas-config prumo
```

3. Optional direct equivalent (same stack file path), useful for troubleshooting:

```bash
docker compose \
  --env-file /home/joao/docker/.env \
  --env-file /home/joao/docker/stacks/web/.env \
  -p jarbas \
  -f /home/joao/docker/stacks/web/compose.yml \
  config
```

4. Capture baseline HTTP checks (save outputs for comparison):

```bash
curl -fsS https://cae.joao.date/healthz
curl -fsS https://joao.date/dados/healthz
curl -fsS https://cae.joao.date/api/ficha
```

Decision point A (Go/No-Go):
- **Go** only if config renders successfully and baseline checks are healthy.
- **No-Go** if compose is invalid, container already unhealthy, or endpoints fail unexpectedly.

---

## 2) Backup procedure (mandatory)

Back up the full appdata tree and make DB-specific copies under `stacks/web/appdata/prumo`.

```bash
set -euo pipefail
TS="$(date +%Y%m%d-%H%M%S)"
SRC="/home/joao/docker/stacks/web/appdata/prumo"
DST_DIR="/home/joao/docker/stacks/web/appdata/_backup_prumo"
mkdir -p "$DST_DIR"

# Full appdata backup
tar -C /home/joao/docker/stacks/web/appdata -czf "$DST_DIR/prumo-$TS.tgz" prumo

# Explicit DB backups (if present)
[ -f "$SRC/cae-data.duckdb" ] && cp -a "$SRC/cae-data.duckdb" "$DST_DIR/cae-data.duckdb.$TS"
[ -f "$SRC/cae-data.db" ] && cp -a "$SRC/cae-data.db" "$DST_DIR/cae-data.db.$TS"

# Manifest for restore confidence
sha256sum "$DST_DIR/prumo-$TS.tgz" > "$DST_DIR/prumo-$TS.tgz.sha256"
ls -lah "$DST_DIR" | tail -n +1
```

Decision point B (Go/No-Go):
- **Go** only when backup tar + checksum exist and DB copies (if present) are confirmed.
- **No-Go** if backup artifacts are missing/incomplete.

---

## 3) Rehearsal (dry-run style)

Goal: verify migration assumptions without changing running containers.

1. Verify effective config still uses expected mounts/networks/service wiring:

```bash
source /home/joao/.bash_aliases
dc-jarbas-config prumo | sed -n '/services:/,/volumes:/p'
```

Check specifically:
- `/home/joao/docker/stacks/web/appdata/prumo:/data:rw`
- expected service name `prumo`
- expected healthcheck on `/healthz`
- expected routes (cae domain + `/dados` path labels)

2. Capture pre-cutover fingerprints of files that bootstrap could touch:

```bash
APPDATA="/home/joao/docker/stacks/web/appdata/prumo"
stat "$APPDATA/site.json" || true
find "$APPDATA/ideologies" -maxdepth 1 -type f -print0 | xargs -0 sha256sum 2>/dev/null || true
[ -f "$APPDATA/README-DB.txt" ] && sha256sum "$APPDATA/README-DB.txt" || true
```

3. Build-only rehearsal if desired (no recreate/up):

```bash
# Optional: build image without switching running container
source /home/joao/.bash_aliases
dc-jarbas build prumo
```

Decision point C (Go/No-Go):
- **Go** if config/mounts are correct and rehearsal checks are consistent.
- **No-Go** if you detect unexpected mount path changes, missing healthcheck, or label drift.

---

## 4) Cutover execution

> This is the only disruptive step.

```bash
source /home/joao/.bash_aliases

# Recreate only prumo service in jarbas stack
# (applies current compose layering and image content)
dc-jarbas-rec prumo
```

Immediately monitor startup:

```bash
source /home/joao/.bash_aliases
dc-jarbas-logs prumo
```

What to watch in logs:
- Expected first-run bootstrap messages only when files are missing:
  - `Initializing default site.json...`
  - `Initializing default ideologies...`
  - `No DuckDB found ... Copying placeholder instructions...`
- Health transitions to healthy without repeated crash loops.

---

## 5) Post-cutover validation

1. Container health and state:

```bash
source /home/joao/.bash_aliases
dc-jarbas-ps prumo
```

2. Endpoint checks:

```bash
curl -fsS https://cae.joao.date/healthz
curl -fsS https://joao.date/dados/healthz
curl -fsS https://cae.joao.date/api/ficha
curl -fsS https://joao.date/dados/api/ficha
```

3. Confirm `/data` bootstrap did **not** overwrite existing data:

```bash
APPDATA="/home/joao/docker/stacks/web/appdata/prumo"

# site.json should preserve local customizations if file already existed
stat "$APPDATA/site.json"

# ideology files should keep prior checksums when they already existed
find "$APPDATA/ideologies" -maxdepth 1 -type f -print0 | xargs -0 sha256sum 2>/dev/null || true

# DB file should still be present and not replaced by placeholder logic
ls -lah "$APPDATA" | egrep 'cae-data\.duckdb|cae-data\.db|README-DB\.txt' || true
```

Interpretation:
- If `site.json`/`ideologies` existed before cutover, bootstrap should not rewrite them.
- `README-DB.txt` should only appear when neither DB file exists.

Decision point D (Go/No-Go):
- **Go** (accept migration) if health is green, key endpoints work, and persisted data is intact.
- **No-Go** if app is unhealthy, critical endpoints fail, or existing `/data` content appears overwritten.

---

## 6) Rollback procedure (fast path)

Trigger rollback if any Decision point after cutover is No-Go.

### 6.1 Immediate service rollback actions

1. Revert repo to previous known-good compose/image refs (git checkout/reset to pre-migration commit).
2. Restore appdata backup if data integrity is in doubt.
3. Recreate only Prumo with known-good state.

Example restore commands:

```bash
set -euo pipefail
TS_OR_FILE="<backup-timestamp-or-filename>"
BACKUP_DIR="/home/joao/docker/stacks/web/appdata/_backup_prumo"
TARGET_BASE="/home/joao/docker/stacks/web/appdata"

# Stop/recreate path handled by stack command later; restore files first when needed.
# WARNING: destructive for current prumo appdata content.
rm -rf "$TARGET_BASE/prumo"
tar -C "$TARGET_BASE" -xzf "$BACKUP_DIR/prumo-$TS_OR_FILE.tgz"

source /home/joao/.bash_aliases
dc-jarbas-rec prumo
```

If only DB must be restored:

```bash
cp -a \
  "/home/joao/docker/stacks/web/appdata/_backup_prumo/cae-data.duckdb.<TS>" \
  "/home/joao/docker/stacks/web/appdata/prumo/cae-data.duckdb"
source /home/joao/.bash_aliases
dc-jarbas-rec prumo
```

### 6.2 Rollback validation

```bash
source /home/joao/.bash_aliases
dc-jarbas-ps prumo
dc-jarbas-logs prumo
curl -fsS https://cae.joao.date/healthz
curl -fsS https://cae.joao.date/api/ficha
```

Rollback success criteria:
- Service stable/healthy.
- Critical endpoints restored.
- Restored data visible and consistent with pre-cutover behavior.

---

## 7) Operator notes

- Keep timestamps and command outputs in an incident/migration log for traceability.
- Do not run collector jobs during cutover window.
- If uncertain about data integrity, prefer full appdata restore from backup over partial/manual edits.
