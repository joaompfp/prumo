#!/usr/bin/env bash
# Authorized code-only replacement of all consumers of ingest.db.
set -euo pipefail
target=${1:?exact approved main SHA required}
[[ $target =~ ^[0-9a-f]{40}$ ]]
repo=/home/joao/docker/stacks/web/images/prumo
receipt=/home/joao/prumo-operations/worker-safety-release-20261123
tag=rollback-worker-safety-20261123
export TMPDIR="$receipt/secret-tmp"
test ! -e "$receipt/pre-activation.json"
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
for service in prumo-ingest prumo prumo-backoffice; do
    test "$(docker inspect --format '{{.Image}}' "$service")" = "$(docker image inspect --format '{{.Id}}' "$service:$tag")"
done
python3 "$receipt/collect.py" --output "$receipt/pre-activation.json"
python3 - "$receipt" "$repo" <<'PY'
import json,sys,subprocess,hashlib
from pathlib import Path
p=Path(sys.argv[1]); repo=sys.argv[2]
a=json.loads((p/'pre-activation.json').read_text())
assert not a['running_runs'], 'Never recreate a worker during a source attempt'
assert subprocess.check_output(['git','-C',repo,'rev-parse','HEAD'],text=True).strip()==a['checkout']
assert a['containers']['prumo-ingest']['running']
include=Path('/home/joao/docker/stacks/web/compose/prumo-ingest.yml')
old=include.read_bytes()
expected=subprocess.check_output(['git','-C',repo,'show',a['checkout']+':deploy/prumo-ingest.yml'])
assert old==expected, 'Unexpected local worker-include changes'
(p/'prumo-ingest-before.yml').write_bytes(old)
paths=('secrets/web.enc.env','stacks/web/compose/prumo-backoffice.yml','stacks/web/images/ifc-viewer/dist-xeokit/index.html')
hashes={path:hashlib.sha256(subprocess.check_output(['git','-C','/home/joao/docker','diff','--binary','--',path])).hexdigest() for path in paths}
(p/'preserved-infra.json').write_text(json.dumps(hashes,indent=2)+'\n')
PY
# Keep the public live binds and every writer stopped while advancing their checkout.
bash -lic 'dc-web stop prumo prumo-backoffice prumo-ingest'
for service in prumo prumo-backoffice prumo-ingest; do
    test "$(docker inspect --format '{{.State.Running}}' "$service")" = false
done
git -C "$repo" merge --ff-only --quiet "$target"
test "$(git -C "$repo" rev-parse HEAD)" = "$target"
install -m 644 "$repo/deploy/prumo-ingest.yml" /home/joao/docker/stacks/web/compose/prumo-ingest.yml
cmp "$repo/deploy/prumo-ingest.yml" /home/joao/docker/stacks/web/compose/prumo-ingest.yml
bash -lic 'dc-web-up prumo-ingest'
bash -lic 'dc-web-up prumo'
bash -lic 'dc-web-up prumo-backoffice'
python3 - "$receipt" "$tag" <<'PY'
import json,subprocess,sys,time
from pathlib import Path
p=Path(sys.argv[1]); tag=sys.argv[2]
services=('prumo-ingest','prumo','prumo-backoffice')
for attempt in range(120):
    rows=json.loads(subprocess.check_output(['docker','inspect',*services]))
    assert all(r['State']['Running'] for r in rows), 'Service not running'
    assert all(r['RestartCount']==0 for r in rows), 'Autonomous restart during activation'
    if all(r['State'].get('Health',{}).get('Status')=='healthy' for r in rows if r['Name']!='/prumo-ingest'):
        break
    time.sleep(1)
else:
    raise SystemExit('Readers not healthy')
images={}
for r in rows:
    n=r['Name'].removeprefix('/')
    expected=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',n+':latest'],text=True).strip()
    recovery=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',n+':'+tag],text=True).strip()
    assert r['Image']==expected and r['Image']!=recovery,n
    images[n]={'container':r['Id'],'actual_image':r['Image'],'rollback':recovery,'started':r['State']['StartedAt'],'restarts':r['RestartCount']}
    if n=='prumo-ingest':
        env=dict(x.split('=',1) for x in r['Config']['Env'] if '=' in x)
        assert env.get('PYTHONFAULTHANDLER')=='1'
        assert r['Config']['User']=='1000:1000'
        assert r['Config']['Cmd']==['python','-u','-m','ingest.scheduler']
(p/'activated-images.json').write_text(json.dumps(images,indent=2)+'\n')
print(json.dumps(images))
PY
python3 "$receipt/collect.py" --output "$receipt/post-activation.json"
python3 "$receipt/verify.py" --baseline "$receipt/pre-activation.json" --current "$receipt/post-activation.json" --output "$receipt/activation-acceptance.json"
