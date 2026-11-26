#!/usr/bin/env bash
# Mount-safe schema-unchanged prebuild. Never use its override for activation.
set -euo pipefail
target=${1:?exact approved main SHA required}
[[ $target =~ ^[0-9a-f]{40}$ ]]
repo=/home/joao/docker/stacks/web/images/prumo
receipt=/home/joao/prumo-operations/selection-ux-release-20261126T133306Z
tag=rollback-selection-ux-20261126T133306Z
test ! -e "$receipt/pre-install.json"
install -d -m 700 "$receipt/secret-tmp"
export TMPDIR="$receipt/secret-tmp"
git -C "$repo" fetch origin
test -z "$(git -C "$repo" status --porcelain)"
test "$(git -C "$repo" rev-parse origin/main)" = "$target"
python3 "$receipt/production_probe.py" --output "$receipt/pre-install.json" --verify
git -C "$repo" worktree add --detach "$receipt/code" "$target"
for service in prumo prumo-backoffice; do
    live=$(docker inspect --format '{{.Image}}' "$service")
    docker image tag "$live" "$service:$tag"
    test "$(docker image inspect --format '{{.Id}}' "$service:$tag")" = "$live"
done
python3 - "$receipt" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = '# Context override only. Never activate with this file.\ninclude: !reset []\nservices:\n'
for name in ('prumo', 'prumo-backoffice'):
    s += f'  {name}:\n    image: {name}:latest\n    build:\n      context: {p}/code\n      dockerfile: Dockerfile\n'
(p / 'prebuild.yml').write_text(s)
PY
bash -lic "dc-web -f '$receipt/prebuild.yml' config --format json" | python3 -c 'import json,sys; c=json.load(sys.stdin); expected=sys.argv[1]; names=("prumo","prumo-backoffice"); assert all(c["services"][n]["build"]["context"]==expected and c["services"][n]["build"]["dockerfile"]=="Dockerfile" for n in names); print("Detached build contexts verified:",expected)' "$receipt/code"
bash -lic "dc-web -f '$receipt/prebuild.yml' build prumo prumo-backoffice"
for service in prumo prumo-backoffice; do
    docker image tag "$service:latest" "$service:prebuilt-selection-ux-20261126T133306Z"
done
python3 "$receipt/production_probe.py" --output "$receipt/post-prebuild.json"
python3 - "$receipt" "$target" <<'PY'
import json,sys,subprocess
from pathlib import Path
p=Path(sys.argv[1]); a=json.loads((p/'pre-install.json').read_text()); b=json.loads((p/'post-prebuild.json').read_text())
for key in ('checkout','containers','schema','migrations','cms','preexisting_infra_diff','unrelated_infra_sha256'):
    assert a[key]==b[key],key
assert subprocess.check_output(['git','-C',str(p/'code'),'rev-parse','HEAD'],text=True).strip()==sys.argv[2]
assert b['quick_check']=='ok' and not b['foreign_keys']
print('Prebuild preserved live code, all services, schema and CMS')
PY
