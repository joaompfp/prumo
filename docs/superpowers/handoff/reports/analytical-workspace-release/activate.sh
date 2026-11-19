#!/usr/bin/env bash
# Authorized UI-only release after exact-commit hosted CI. Normal aliases for activation.
set -euo pipefail
repo=/home/joao/docker/stacks/web/images/prumo
receipt=/home/joao/prumo-operations/analytical-workspace-release-20261119T164616Z
target=913eb2fff75dbaf3447b58091f69c2bb43e96fda
old=361eca76d0fb2536c130d9f5315d8251cec07b96
tag=rollback-analytical-workspace-20261119T164616Z
python3 - "$receipt/ci.json" "$target" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert r['headSha']==sys.argv[2] and r['status']=='completed' and r['conclusion']=='success'
assert r['databaseId']==44569621926 and r['event']=='push' and r['headBranch']=='main' and r['workflowName']=='CI'
assert r['jobs'] and all(j['conclusion']=='success' for j in r['jobs'])
print('Exact-release hosted CI passed:',r['url'])
PY
git -C "$repo" fetch origin
test -z "$(git -C "$repo" status --porcelain)"
test "$(git -C "$repo" rev-parse HEAD)" = "$old"
test "$(git -C "$repo" rev-parse origin/main)" = "$target"
for service in prumo prumo-backoffice; do
  test "$(docker inspect --format '{{.Image}}' "$service")" = "$(docker image inspect --format '{{.Id}}' "$service:$tag")"
done
export TMPDIR="$receipt/secret-tmp"
python3 "$repo/docs/superpowers/handoff/reports/tabler-ui/production_probe.py" --output "$receipt/pre-activation.json"
# Only public web has live app/static binds. Keep worker and CMS content untouched.
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
prebuilt=json.loads((p/'prebuilt-images.json').read_text())
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
    assert r['Image']==prebuilt[n], 'Activation differs from verified prebuild: '+n
    images[n]={'container':r['Id'],'actual_image':r['Image'],'latest':expected,'rollback':recovery}
(p/'activated-images.json').write_text(json.dumps(images,indent=2))
print(json.dumps(images))
PY
python3 "$repo/docs/superpowers/handoff/reports/tabler-ui/production_probe.py" --output "$receipt/post-install.json" --baseline "$receipt/pre-activation.json" --verify
python3 "$repo/docs/superpowers/handoff/reports/notebook-navigation-release/preview_probe.py" --output "$receipt/preview.json"
docker image inspect --format '{{.Id}} {{json .RepoTags}}' "prumo:$tag" "prumo-backoffice:$tag"
