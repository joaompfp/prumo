#!/usr/bin/env bash
# Authorized reader-only activation after exact-main hosted CI.
set -euo pipefail
target=${1:?exact approved main SHA required}
[[ $target =~ ^[0-9a-f]{40}$ ]]
repo=/home/joao/docker/stacks/web/images/prumo
receipt=/home/joao/prumo-operations/significant-figures-release-20261125T195130Z
tag=rollback-significant-20261125T195130Z
export TMPDIR="$receipt/secret-tmp"
python3 - "$receipt/ci.json" "$target" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r['headSha']==sys.argv[2] and r['status']=='completed' and r['conclusion']=='success'
assert r['event']=='push' and r['headBranch']=='main' and r['workflowName']=='CI'
assert r['jobs'] and all(j['conclusion']=='success' for j in r['jobs'])
print('Exact-release hosted CI passed:',r['url'])
PY
git -C "$repo" fetch origin
test -z "$(git -C "$repo" status --porcelain)"
test "$(git -C "$repo" rev-parse origin/main)" = "$target"
python3 - "$receipt/pre-install.json" "$repo" <<'PY'
import json,sys,subprocess
from pathlib import Path
before=json.loads(Path(sys.argv[1]).read_text())
assert subprocess.check_output(['git','-C',sys.argv[2],'rev-parse','HEAD'],text=True).strip()==before['checkout']
PY
for service in prumo prumo-backoffice; do
    test "$(docker inspect --format '{{.Image}}' "$service")" = "$(docker image inspect --format '{{.Id}}' "$service:$tag")"
done
python3 "$receipt/production_probe.py" --output "$receipt/pre-activation.json" --verify
bash -lic 'dc-web stop prumo'
test "$(docker inspect --format '{{.State.Running}}' prumo)" = false
git -C "$repo" merge --ff-only --quiet "$target"
test "$(git -C "$repo" rev-parse HEAD)" = "$target"
bash -lic 'dc-web-up prumo'
bash -lic 'dc-web-up prumo-backoffice'
python3 - "$receipt" "$tag" <<'PY'
import json,subprocess,sys,time
from pathlib import Path
p=Path(sys.argv[1]); tag=sys.argv[2]
for attempt in range(90):
    rows=json.loads(subprocess.check_output(['docker','inspect','prumo','prumo-backoffice']))
    assert all(r['State']['Running'] for r in rows),'Reader not running'
    if all(r['State'].get('Health',{}).get('Status')=='healthy' for r in rows): break
    time.sleep(1)
else: raise SystemExit('Readers not healthy')
images={}
for r in rows:
    n=r['Name'].removeprefix('/')
    expected=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',n+':latest'],text=True).strip()
    recovery=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',n+':'+tag],text=True).strip()
    assert r['Image']==expected and r['Image']!=recovery,n
    images[n]={'container':r['Id'],'actual_image':r['Image'],'latest':expected,'rollback':recovery}
(p/'activated-images.json').write_text(json.dumps(images,indent=2))
print(json.dumps(images))
PY
python3 "$receipt/production_probe.py" --output "$receipt/post-install.json" --baseline "$receipt/pre-activation.json" --verify
python3 "$receipt/preview_probe.py" --output "$receipt/preview.json"
for service in prumo prumo-backoffice; do
    docker image inspect --format '{{.Id}} {{json .RepoTags}}' "$service:$tag"
done
