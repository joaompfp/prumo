"""Exercise stop/readback fail-closed ordering in the exact activation shell script.

All external commands are stubs under the approved scratch root. This proves shell
control flow only; actual CI, images, data and readiness are verified separately.
"""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

STUB = '''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
args=sys.argv[1:]
with open(os.environ['PROBE_LOG'],'a') as f:
    f.write(json.dumps([name,*args])+'\\n')
if name=='git':
    if 'rev-parse' in args:
        print(os.environ['PROBE_TARGET'])
    if 'merge' in args and os.environ.get('PROBE_MERGE_FAIL')=='1':
        sys.exit(9)
elif name=='docker':
    if '{{.Image}}' in args or '{{.Id}}' in args:
        print('old-exact-image')
    elif '{{.State.Running}}' in args:
        print('true' if os.environ.get('PROBE_READBACK_FAIL')=='1' else 'false')
elif name=='bash' and 'dc-web stop ' in ' '.join(args):
    sys.exit(int(os.environ.get('PROBE_STOP_RC','0')))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = []
    with tempfile.TemporaryDirectory(prefix="prumo-activation-guards-", dir="/home/joao/.hermes/cache/scratch") as directory:
        root = Path(directory)
        bins = root / "bin"
        bins.mkdir()
        for name in ("python3", "docker", "git", "bash", "install", "cmp"):
            file = bins / name
            file.write_text(STUB)
            file.chmod(0o700)
        for label, changes, expected in (
            ("success", {}, 0),
            ("stop-failure", {"PROBE_STOP_RC": "7"}, 7),
            ("stopped-readback-failure", {"PROBE_READBACK_FAIL": "1"}, 1),
            ("checkout-failure", {"PROBE_MERGE_FAIL": "1"}, 9),
        ):
            log = root / (label + ".jsonl")
            env = {**os.environ, "PATH": str(bins) + ":/usr/bin:/bin", "PROBE_LOG": str(log), "PROBE_TARGET": "a" * 40, **changes}
            process = subprocess.run(["/bin/bash", str(args.script.resolve()), "a" * 40], env=env, capture_output=True, text=True)
            commands = [json.loads(line) for line in log.read_text().splitlines()]
            assert process.returncode == expected, (label, process.returncode, process.stderr)
            up = [i for i, command in enumerate(commands) if command[0] == "bash" and "dc-web-up " in " ".join(command)]
            installs = [i for i, command in enumerate(commands) if command[0] == "install"]
            merges = [i for i, command in enumerate(commands) if command[0] == "git" and "merge" in command]
            if expected:
                assert not up and not installs, (label, commands)
                if label != "checkout-failure":
                    assert not merges, (label, commands)
            else:
                assert len(up) == 3 and len(installs) == len(merges) == 1
                assert merges[0] < installs[0] < up[0]
                assert [commands[i][-1] for i in up] == ["dc-web-up prumo-ingest", "dc-web-up prumo", "dc-web-up prumo-backoffice"]
            cases.append({"case": label, "passed": True, "exit_code": process.returncode, "commands": commands})
    args.output.write_text(json.dumps({"cases": cases, "scope": "stubbed shell control flow only"}, indent=2) + "\n")
    print(json.dumps({"passed": len(cases), "scope": "stubbed shell control flow only"}))


if __name__ == "__main__":
    main()
