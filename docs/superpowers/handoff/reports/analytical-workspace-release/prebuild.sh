#!/usr/bin/env bash
set -euo pipefail
repo=/home/joao/docker/stacks/web/images/prumo
receipt=/home/joao/prumo-operations/analytical-workspace-release-20261119T164616Z
target=913eb2fff75dbaf3447b58091f69c2bb43e96fda
old=361eca76d0fb2536c130d9f5315d8251cec07b96
tag=rollback-analytical-workspace-20261119T164616Z
test -z "$(git -C "$repo" status --porcelain)"
test "$(git -C "$repo" rev-parse HEAD)" = "$old"
install -d -m 700 "$receipt/secret-tmp"
export TMPDIR="$receipt/secret-tmp"
git -C "$repo" fetch origin
test "$(git -C "$repo" rev-parse origin/main)" = "$target"
git -C "$repo" worktree add --detach "$receipt/code" "$target"
python3 "$repo/docs/superpowers/handoff/reports/tabler-ui/production_probe.py" --output "$receipt/pre-install.json" --verify
for service in prumo prumo-backoffice; do
  live=$(docker inspect --format '{{.Image}}' "$service")
  docker image tag "$live" "$service:$tag"
  test "$(docker image inspect --format '{{.Id}}' "$service:$tag")" = "$live"
done
bash -lic "dc-web -f '$receipt/prebuild.yml' config --format json" | python3 -c 'import json,sys; c=json.load(sys.stdin); expected=sys.argv[1]; names=("prumo","prumo-backoffice"); assert all(c["services"][n]["build"]["context"]==expected and c["services"][n]["build"]["dockerfile"]=="Dockerfile" for n in names); print("Detached build contexts verified",expected)' "$receipt/code"
bash -lic "dc-web -f '$receipt/prebuild.yml' build prumo prumo-backoffice"
python3 "$repo/docs/superpowers/handoff/reports/tabler-ui/production_probe.py" --output "$receipt/post-prebuild.json"
python3 - "$receipt" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); a=json.loads((p/'pre-install.json').read_text()); b=json.loads((p/'post-prebuild.json').read_text())
for key in ('checkout','containers','schema','migrations','cms','preexisting_infra_diff'):
    assert a[key]==b[key],key
assert b['quick_check']=='ok' and not b['foreign_keys']
print('Prebuild preserved live checkout, services, worker, schema and CMS')
PY
