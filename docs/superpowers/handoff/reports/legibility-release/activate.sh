#!/usr/bin/env bash
# Run only after the controller has verified CI for the exact target below.
set -euo pipefail
repo=/home/joao/docker/stacks/web/images/prumo
receipt=/home/joao/prumo-operations/legibility-release-20261117T224217Z
target=9d122f90b9307b3a4a3848e5d7b99b92a9b27ca9
old=6f851d4a5527b32613a434c1690e1228c70b7dd8

test -z "$(git -C "$repo" status --porcelain)"
test "$(git -C "$repo" rev-parse HEAD)" = "$old"
test "$(git -C "$repo" rev-parse origin/main)" = "$target"
docker image inspect prumo:rollback-legibility-20261117T224217Z >/dev/null
docker image inspect prumo-backoffice:rollback-legibility-20261117T224217Z >/dev/null
python3 "$repo/docs/superpowers/handoff/reports/tabler-ui/production_probe.py" \
    --output "$receipt/pre-activation.json"

# app/ and static/ are live bind mounts: stop only this reader before advancing them.
bash -lic 'dc-web stop prumo'
test "$(docker inspect --format '{{.State.Running}}' prumo)" = false
git -C "$repo" merge --ff-only --quiet "$target"
test "$(git -C "$repo" rev-parse HEAD)" = "$target"
# Use the normal runtime includes and encrypted environments, not the build-only override.
bash -lic 'dc-web-up prumo'
bash -lic 'dc-web-up prumo-backoffice'
docker inspect --format '{{.Name}}|{{.Id}}|{{.Image}}|{{.State.StartedAt}}|{{.RestartCount}}' \
    prumo prumo-ingest prumo-backoffice
