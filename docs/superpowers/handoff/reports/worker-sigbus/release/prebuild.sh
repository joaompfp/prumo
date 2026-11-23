#!/usr/bin/env bash
# Build exact approved code without changing any running service or live bind.
set -euo pipefail
target=${1:?exact approved main SHA required}
[[ $target =~ ^[0-9a-f]{40}$ ]]
repo=/home/joao/docker/stacks/web/images/prumo
receipt=/home/joao/prumo-operations/worker-safety-release-20261123
tag=rollback-worker-safety-20261123
export TMPDIR="$receipt/secret-tmp"
test ! -e "$receipt/prebuild-start.json"
git -C "$repo" fetch origin
test -z "$(git -C "$repo" status --porcelain)"
test "$(git -C "$repo" rev-parse origin/main)" = "$target"
python3 "$receipt/collect.py" --output "$receipt/prebuild-start.json"
git -C "$repo" worktree add --detach "$receipt/code" "$target"
for service in prumo-ingest prumo prumo-backoffice; do
    live=$(docker inspect --format '{{.Image}}' "$service")
    docker image tag "$live" "$service:$tag"
    test "$(docker image inspect --format '{{.Id}}' "$service:$tag")" = "$live"
done
python3 - "$receipt" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = '# Build context only. NEVER use this file for up.\ninclude: !reset []\nservices:\n'
for name in ('prumo-ingest', 'prumo', 'prumo-backoffice'):
    s += f'  {name}:\n    image: {name}:latest\n    build:\n      context: {p}/code\n      dockerfile: Dockerfile\n'
(p / 'prebuild.yml').write_text(s)
PY
bash -lic "dc-web -f '$receipt/prebuild.yml' config --format json" | python3 -c 'import json,sys; c=json.load(sys.stdin); expected=sys.argv[1]; names=("prumo-ingest","prumo","prumo-backoffice"); assert all(c["services"][n]["build"]["context"]==expected and c["services"][n]["build"]["dockerfile"]=="Dockerfile" for n in names); print("Detached build contexts verified:",expected)' "$receipt/code"
bash -lic "dc-web -f '$receipt/prebuild.yml' build prumo-ingest prumo prumo-backoffice"
for service in prumo-ingest prumo prumo-backoffice; do
    docker image tag "$service:latest" "$service:prebuilt-worker-safety-20261123"
done
python3 "$receipt/collect.py" --output "$receipt/post-prebuild.json"
python3 - "$receipt" "$target" <<'PY'
import json,sys,subprocess
from pathlib import Path
p=Path(sys.argv[1]); a=json.loads((p/'prebuild-start.json').read_text()); b=json.loads((p/'post-prebuild.json').read_text())
for report in (a, b):
    for item in report['containers'].values():
        item['mounts'] = sorted(item['mounts'], key=lambda mount: mount['target'])
for key in ('checkout','containers','schema','migrations'):
    assert a[key]==b[key],key
for table in ('cms_document','cms_revision','cms_event','editorial_page','editorial_slot','editorial_event'):
    assert a['tables'][table]==b['tables'][table],table
assert subprocess.check_output(['git','-C',str(p/'code'),'rev-parse','HEAD'],text=True).strip()==sys.argv[2]
assert b['quick_check']=='ok' and not b['foreign_keys']
print('Prebuild preserved live code, all services, schema and CMS')
PY
