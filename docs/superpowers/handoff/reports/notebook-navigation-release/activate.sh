#!/usr/bin/env bash
# Authorized schema-unchanged web/Admin release, after exact-SHA hosted CI.
set -euo pipefail
repo=/home/joao/docker/stacks/web/images/prumo
receipt=/home/joao/prumo-operations/notebook-navigation-release-20261118T074000Z
target=361eca76d0fb2536c130d9f5315d8251cec07b96
old=24a3dc7ed824933d4bd1130662b62b9908c9783b

python3 - "$receipt/ci.json" "$target" <<'PY'
import json
import sys
from pathlib import Path
report = json.loads(Path(sys.argv[1]).read_text())
assert report['headSha'] == sys.argv[2]
assert report['status'] == 'completed' and report['conclusion'] == 'success'
print('Exact-release hosted CI passed:', report['url'])
PY

test -z "$(git -C "$repo" status --porcelain)"
test "$(git -C "$repo" rev-parse HEAD)" = "$old"
test "$(git -C "$repo" rev-parse origin/main)" = "$target"
docker image inspect prumo:rollback-notebook-navigation-20261118T074000Z >/dev/null
docker image inspect prumo-backoffice:rollback-notebook-navigation-20261118T074000Z >/dev/null
for service in prumo prumo-backoffice; do
    live=$(docker inspect --format '{{.Image}}' "$service")
    recovery=$(docker image inspect --format '{{.Id}}' "$service:rollback-notebook-navigation-20261118T074000Z")
    test "$live" = "$recovery"
done
mkdir -m 700 "$receipt/secret-tmp"
export TMPDIR="$receipt/secret-tmp"
python3 "$repo/docs/superpowers/handoff/reports/tabler-ui/production_probe.py" \
    --output "$receipt/pre-activation.json"

# Public app/static bind mounts are live. Stop only this reader before changing them.
bash -lic 'dc-web stop prumo'
test "$(docker inspect --format '{{.State.Running}}' prumo)" = false
git -C "$repo" merge --ff-only --quiet "$target"
test "$(git -C "$repo" rev-parse HEAD)" = "$target"
# Use the normal runtime includes, never the context-only prebuild manifest.
bash -lic 'dc-web-up prumo'
bash -lic 'dc-web-up prumo-backoffice'
python3 - <<'PY'
import json
import subprocess
import time
for attempt in range(90):
    rows = json.loads(subprocess.check_output(['docker', 'inspect', 'prumo', 'prumo-backoffice']))
    if all(row['State'].get('Health', {}).get('Status') == 'healthy' for row in rows):
        break
    if any(not row['State']['Running'] for row in rows):
        raise SystemExit('A recreated reader is not running')
    time.sleep(1)
else:
    raise SystemExit('Readers did not become healthy')
print('Both readers are healthy')
from pathlib import Path
images = {}
for row in rows:
    name = row['Name'].removeprefix('/')
    expected = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', name + ':latest'], text=True).strip()
    previous = subprocess.check_output(['docker', 'image', 'inspect', '--format', '{{.Id}}', name + ':rollback-notebook-navigation-20261118T074000Z'], text=True).strip()
    assert row['Image'] == expected and row['Image'] != previous, name
    images[name] = {'container': row['Id'], 'actual_image': row['Image'], 'latest': expected, 'rollback': previous}
Path('/home/joao/prumo-operations/notebook-navigation-release-20261118T074000Z/activated-images.json').write_text(json.dumps(images, indent=2))
print(json.dumps(images))
PY
python3 "$repo/docs/superpowers/handoff/reports/tabler-ui/production_probe.py" \
    --output "$receipt/post-install.json" --baseline "$receipt/pre-activation.json" --verify
docker image inspect --format '{{.Id}} {{json .RepoTags}}' \
    prumo:rollback-notebook-navigation-20261118T074000Z \
    prumo-backoffice:rollback-notebook-navigation-20261118T074000Z
