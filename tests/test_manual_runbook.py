"""Execute the authoritative manual-write fence offline, never real operator commands."""

import re
import subprocess
from pathlib import Path

import pytest

OPERATIONS = Path(__file__).resolve().parents[1] / "docs/data/operations.md"


def manual_fence():
    section = OPERATIONS.read_text(encoding="utf-8").split(
        "## Manual update with original response bundles\n", 1
    )[1].split("\n## ", 1)[0]
    return re.search(r"```bash\n(.*?)```", section, re.DOTALL).group(1)


# Only shell builtins and these in-memory functions can run. The empty PATH and
# DEBUG allowlist also reject accidental new/absolute external commands, including
# inside substitutions. Events go to captured stdout, not files written by the fence.
STUBS = r'''
set +e
set -T
PATH=/no-external-commands
BUNDLE_HOST='/captured/bundle with spaces'
BUNDLE_SOURCE=$SOURCE
BUNDLE_FROM=2026-11-10
BUNDLE_TO=2026-11-11
INDICATOR=SP.POP.TOTL
basename() {
    [[ "$*" == '-- /captured/bundle with spaces' ]] || exit 98
    printf '%s\n' 'bundle with spaces'
}
test() {
    [[ "$*" == '-f /captured/bundle with spaces/manifest.json' ]] || exit 98
    printf '%s\n' manifest
    return 0
}
bash() {
    [[ "$*" == '-lic dc-web stop prumo-ingest' ]] || exit 98
    printf '%s\n' stop
    [[ "$FAIL_AT" != stop ]] || return 21
}
docker() {
    local event
    case "$*" in
        "inspect prumo-ingest --format {{.State.Running}}")
            printf '%s\n' readback >&2
            [[ "$FAIL_AT" != inspect ]] || return 22
            if [[ "$FAIL_AT" == running ]]; then printf 'true\n'; else printf 'false\n'; fi
            return 0 ;;
        'exec prumo mkdir -p /data/migration/bundles') event=mkdir ;;
        'exec prumo test ! -e /data/migration/bundles/bundle with spaces') event=refusal ;;
        'cp /captured/bundle with spaces prumo:/data/migration/bundles/bundle with spaces')
            [[ "$#" == 3 ]] || exit 98
            event=copy ;;
        'exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw run '* )
            [[ "${10}" == run && "${12}" == --bundle && "${13}" == '/data/migration/bundles/bundle with spaces' ]] || exit 98
            if [[ "$SOURCE" == worldbank ]]; then
                [[ "${14}" == --indicator && "${15}" == SP.POP.TOTL && "$#" == 15 ]] || exit 98
            else
                [[ "${14}" == --from && "${15}" == 2026-11-10 && "${16}" == --to && "${17}" == 2026-11-11 && "$#" == 17 ]] || exit 98
            fi
            event=import ;;
        'exec prumo python -m ingest --db /data/prumo.sqlite3 --raw-dir /data/raw status --json')
            event=status ;;
        *) printf 'UNEXPECTED docker: %s\n' "$*" >&2; exit 98 ;;
    esac
    printf '%s\n' "$event"
    [[ "$FAIL_AT" != "$event" ]] || return 23
    return 0
}
trap 'case "$BASH_COMMAND" in
    set\ *|case\ *|:\ *|\[\[\ *|test\ *|basename\ *|BUNDLE_*|WORKER_RUNNING=*|RUN_ARGS=*|RUN_ARGS+=*|bash\ *|docker\ *|printf\ *|exit\ *|return\ *|local\ *|event=*|manual_rc=*) ;;
    *) printf "UNEXPECTED command: %s\n" "$BASH_COMMAND" >&2; exit 99 ;;
esac' DEBUG
'''


def run_manual(tmp_path, *, fail_at="", source="worldbank"):
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc"],
        input=STUBS + "\n" + manual_fence() + r'''
manual_rc=$?
printf 'parent-alive\n'
[[ $- != *e* ]] || exit 97
exit "$manual_rc"
''',
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env={"FAIL_AT": fail_at, "SOURCE": source, "LC_ALL": "C"},
        timeout=10,
    )
    assert "UNEXPECTED" not in result.stderr, result.stderr
    assert list(tmp_path.iterdir()) == [], "fence must not write harness files"
    return result, result.stdout.splitlines()


@pytest.mark.parametrize("failure", ["stop", "inspect", "running", "mkdir", "refusal", "copy"])
def test_manual_prerequisite_failure_prevents_independent_writer(tmp_path, failure):
    result, events = run_manual(tmp_path, fail_at=failure)
    assert result.returncode != 0, (events, result.stderr)
    assert "import" not in events
    if failure != "copy":
        assert "copy" not in events
    assert "status" not in events
    assert events[-1] == "parent-alive", "must not exit the operator parent shell"
    if failure == "stop":
        assert "readback" not in result.stderr
        assert events == ["manifest", "stop", "parent-alive"]
    elif failure in {"inspect", "running"}:
        assert "readback" in result.stderr
        assert "mkdir" not in events


def test_manual_failed_import_not_masked_by_otherwise_successful_status(tmp_path):
    result, events = run_manual(tmp_path, fail_at="import")
    assert result.returncode == 23, (events, result.stderr)
    assert events == ["manifest", "stop", "mkdir", "refusal", "copy", "import", "parent-alive"]
    assert "readback" in result.stderr
    # Diagnostic status would return zero (exercised on the successful path), but
    # fail-closed execution must not reach it after the failed import.


@pytest.mark.parametrize("source", ["worldbank", "eredes"])
def test_manual_success_orders_stop_readback_copy_import_status_without_restart(tmp_path, source):
    result, events = run_manual(tmp_path, source=source)
    assert result.returncode == 0, (events, result.stderr)
    assert events == ["manifest", "stop", "mkdir", "refusal", "copy", "import", "status", "parent-alive"]
    assert result.stderr.splitlines() == ["readback"]


def test_manual_invalid_source_does_not_exit_parent_or_stop_worker(tmp_path):
    result, events = run_manual(tmp_path, source="unsupported")
    assert result.returncode == 2
    assert "stop" not in events
    assert events[-1] == "parent-alive"


def test_manual_fence_has_valid_bash_syntax():
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-n"],
        input=manual_fence(), text=True, capture_output=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
