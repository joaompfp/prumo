"""Offline contracts for the shared web/ingest image and worker deployment candidate.

These inspect repository inputs and execute the real entrypoint with mkdir isolated
by a test double. Image builds, full-suite runs and production acceptance belong to
the controller; no Docker daemon or publisher network is used here.
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
COMPOSE = REPO / "deploy/prumo-ingest.yml"
OPERATIONS = REPO / "docs/data/operations.md"


@pytest.fixture(scope="module")
def instructions():
    text = (REPO / "Dockerfile").read_text(encoding="utf-8")
    text = re.sub(r"[ \t]*\\\n[ \t]*", " ", text)
    result = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, value = line.split(maxsplit=1)
        result.setdefault(name.upper(), []).append(value)
    return result


def test_image_copies_only_runtime_inputs_including_registry_and_migrations(instructions):
    copies = [shlex.split(value) for value in instructions["COPY"]]
    assert copies == [
        ["requirements.txt", "."],
        ["app/", "./app/"],
        ["static/", "./static/"],
        ["ingest/", "./ingest/"],
        ["backoffice/", "./backoffice/"],
        ["registry/", "./registry/"],
        ["entrypoint.sh", "./"],
    ]
    assert "ADD" not in instructions
    assert (REPO / "ingest/migrations/0001_init.sql").is_file()
    assert (REPO / "registry/core.yaml").is_file()


def test_image_defaults_are_sqlite_and_raw_evidence_not_legacy_or_secrets(instructions):
    env = dict(token.split("=", 1) for line in instructions["ENV"]
               for token in shlex.split(line))
    assert env == {
        "PRUMO_DB_PATH": "/data/prumo.sqlite3",
        "PRUMO_RAW_DIR": "/data/raw",
    }
    assert "ARG" not in instructions
    assert instructions["FROM"] == ["python:3.12-slim"]
    assert instructions["WORKDIR"] == ["/app"]
    assert instructions["RUN"] == [
        "pip install --no-cache-dir -r requirements.txt",
        "chmod +x ./entrypoint.sh",
    ]


def test_web_default_command_and_http_healthcheck_are_preserved(instructions):
    assert json.loads(instructions["ENTRYPOINT"][0]) == ["./entrypoint.sh"]
    assert json.loads(instructions["CMD"][0]) == [
        "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1",
    ]
    assert instructions["EXPOSE"] == ["8080"]
    assert instructions["HEALTHCHECK"] == [
        '--interval=5s --timeout=3s --start-period=15s --retries=3 '
        'CMD python3 -c "import urllib.request; '
        "urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)\" || exit 1"
    ]


def test_build_context_is_deny_by_default_with_only_runtime_reinclusions():
    rules = [line.strip() for line in (REPO / ".dockerignore").read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    assert rules[0] == "**"
    allowed = {
        "!Dockerfile", "!.dockerignore", "!requirements.txt", "!entrypoint.sh",
        "!app/", "!app/**", "!static/", "!static/**",
        "!ingest/", "!ingest/**", "!backoffice/", "!backoffice/**",
        "!registry/", "!registry/**",
    }
    assert {rule for rule in rules if rule.startswith("!")} == allowed
    last_allow = max(i for i, rule in enumerate(rules) if rule.startswith("!"))
    exclusions = set(rules[last_allow + 1:])
    assert {
        "**/.git", "**/.venv*", "**/venv*", "**/__pycache__", "**/*.py[cod]",
        "**/.pytest_cache", "**/.ruff_cache", "**/.env", "**/.env.*",
        "**/*.env", "**/*.env.*", "**/*.pem", "**/*.key", "**/*.p12", "**/*.pfx",
        "**/.netrc", "**/.npmrc", "**/.pypirc", "**/.git-credentials",
        "**/.ssh", "**/.aws", "**/.secrets*", "**/credentials*", "**/secrets*",
        "**/*.sqlite*", "**/*.db", "**/*.duckdb*",
    } <= exclusions
    # Docs, fixtures, historical data, scripts and local artifacts cannot be re-included.
    assert not any(any(part in rule for part in (
        "collectors", "scripts", "seed_data", "tests", "docs", "appdata", "reports",
    )) for rule in allowed)


@pytest.fixture
def entrypoint_env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    mkdir = bin_dir / "mkdir"
    mkdir.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$PRUMO_TEST_MKDIR_LOG"\n'
        'exit "${PRUMO_TEST_MKDIR_EXIT:-0}"\n',
        encoding="utf-8",
    )
    mkdir.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "PRUMO_TEST_MKDIR_LOG": str(tmp_path / "mkdir-args"),
    }


def test_entrypoint_has_only_directory_setup_and_exec():
    lines = [line.strip() for line in (REPO / "entrypoint.sh").read_text().splitlines()
             if line.strip()]
    assert lines == ["#!/bin/sh", "set -e", "mkdir -p /data", 'exec "$@"']


@pytest.mark.parametrize("exit_code", [0, 23])
def test_entrypoint_exec_preserves_pid_arguments_and_exit_status(entrypoint_env, exit_code):
    code = (
        "import json, os, sys; print(json.dumps({'pid': os.getpid(), 'args': sys.argv[1:]})); "
        f"sys.exit({exit_code})"
    )
    args = ["two words", "$untouched", "--flag"]
    with subprocess.Popen(
        ["/bin/sh", str(REPO / "entrypoint.sh"), sys.executable, "-c", code, *args],
        env=entrypoint_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ) as proc:
        stdout, stderr = proc.communicate(timeout=10)
        assert proc.returncode == exit_code
        assert stderr == ""
        assert json.loads(stdout) == {"pid": proc.pid, "args": args}
    assert Path(entrypoint_env["PRUMO_TEST_MKDIR_LOG"]).read_text().splitlines() == [
        "-p", "/data",
    ]


def test_entrypoint_does_not_start_command_when_directory_creation_fails(entrypoint_env):
    result = subprocess.run(
        ["/bin/sh", str(REPO / "entrypoint.sh"), sys.executable, "-c", "print('started')"],
        env={**entrypoint_env, "PRUMO_TEST_MKDIR_EXIT": "73"},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 73
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.fixture(scope="module")
def worker():
    assert COMPOSE.is_file(), "repository deployment candidate is missing"
    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert set(document) == {"services"}
    assert set(document["services"]) == {"prumo-ingest"}
    return document["services"]["prumo-ingest"]


def test_worker_build_and_command_are_distinct_from_web(worker):
    assert worker["build"] == {
        "context": "${DOCKER_DIR}/stacks/web/images/prumo", "dockerfile": "Dockerfile",
    }
    assert worker["image"] == "prumo-ingest:latest"
    assert worker["container_name"] == "prumo-ingest"
    assert worker["command"] == ["python", "-u", "-m", "ingest.scheduler"]
    assert worker["healthcheck"] == {"disable": True}


def test_worker_has_bounded_resources_logs_and_no_public_surface(worker):
    assert worker["restart"] == "unless-stopped"
    assert worker["mem_limit"] == "512m"
    assert worker["security_opt"] == ["no-new-privileges:true"]
    assert worker["networks"] == ["t2_proxy"]
    assert worker["logging"] == {
        "driver": "json-file", "options": {"max-size": "10m", "max-file": "3"},
    }
    assert set(worker) == {
        "build", "image", "container_name", "command", "restart", "mem_limit",
        "security_opt", "logging", "networks", "volumes", "environment", "healthcheck",
    }


def test_worker_shares_persistent_data_dns_and_only_source_secret(worker):
    assert worker["volumes"] == [
        "${DOCKER_DIR}/stacks/web/appdata/prumo:/data:rw",
        "${DOCKER_DIR}/resolv.conf:/etc/resolv.conf:ro",
    ]
    assert worker["environment"] == {
        "TZ": "${TZ}",
        "PRUMO_DB_PATH": "/data/prumo.sqlite3",
        "PRUMO_RAW_DIR": "/data/raw",
        "PYTHONUNBUFFERED": "1",
        "FRED_API_KEY": "${FRED_API_KEY:-}",
    }


def test_operator_runbook_links_authoritative_manual_refresh_and_has_valid_shell():
    assert OPERATIONS.is_file(), "operator runbook is missing"
    text = OPERATIONS.read_text(encoding="utf-8")
    assert "(manual-refresh.md)" in text
    assert "ingest capture" not in text, "keep capture procedure authoritative in manual-refresh.md"
    scripts = re.findall(r"```bash\n(.*?)```", text, re.DOTALL)
    assert scripts, "operator runbook needs exact commands"
    for script in scripts:
        result = subprocess.run(
            ["/bin/bash", "-n"], input=script, capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, result.stderr
    assert "docker compose" not in "\n".join(scripts)
    assert "docker run" not in "\n".join(scripts)


def _requirement_names(path: Path) -> set[str]:
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            names.add(re.split(r"[<>=!~\[ ;]", line, maxsplit=1)[0].lower())
    return names


def test_test_only_packages_stay_out_of_the_production_image():
    """The image installs requirements.txt only (D-M7); pytest and friends live in
    requirements-dev.txt, which the deny-by-default build context never includes."""
    runtime = _requirement_names(REPO / "requirements.txt")
    dev = _requirement_names(REPO / "requirements-dev.txt")
    test_only = {"pytest", "pytest-cov", "httpx"}
    assert not runtime & test_only, runtime & test_only
    assert test_only <= dev
    assert {"fastapi", "uvicorn", "requests", "pydantic", "pyyaml", "jinja2"} <= runtime
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "requirements-dev.txt" in ci


# --- backoffice (read-only operator view, Tailscale-only) -------------------------------------

BACKOFFICE = REPO / "deploy/prumo-backoffice.yml"


@pytest.fixture(scope="module")
def backoffice_document():
    assert BACKOFFICE.is_file(), "backoffice deployment candidate is missing"
    return yaml.safe_load(BACKOFFICE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def backoffice(backoffice_document):
    assert set(backoffice_document) == {"services", "networks"}
    assert set(backoffice_document["services"]) == {"prumo-backoffice"}
    return backoffice_document["services"]["prumo-backoffice"]


def test_backoffice_image_inputs_exist():
    """The image carries backoffice/ (code + templates) and the registry notes it reads."""
    assert (REPO / "backoffice/app.py").is_file()
    assert (REPO / "backoffice/templates/base.html").is_file()
    assert list((REPO / "registry").glob("unmapped-*.md"))


def test_backoffice_has_its_own_image_tag_and_runs_the_factory(backoffice):
    """Same Dockerfile, but its own tag: a backoffice deploy never retags the worker's image."""
    assert backoffice["build"] == {
        "context": "${DOCKER_DIR}/stacks/web/images/prumo", "dockerfile": "Dockerfile",
    }
    assert backoffice["image"] == "prumo-backoffice:latest"
    assert backoffice["container_name"] == "prumo-backoffice"
    assert backoffice["command"] == [
        "uvicorn", "backoffice.app:app_from_env", "--factory",
        "--host", "0.0.0.0", "--port", "8080", "--workers", "1",
    ]
    from backoffice.app import app_from_env
    assert callable(app_from_env)


def test_backoffice_is_tailscale_only_and_mounts_data_read_only(backoffice):
    assert backoffice["ports"] == ["100.118.19.6:8089:8080"]
    assert "labels" not in backoffice  # no Traefik route
    # no resolv.conf: the app makes no outbound call and no lookup (see the no-egress test)
    assert backoffice["volumes"] == ["${DOCKER_DIR}/stacks/web/appdata/prumo:/data:ro"]
    assert backoffice["environment"] == {
        "TZ": "${TZ}",
        "PRUMO_DB_PATH": "/data/prumo.sqlite3",
        "PRUMO_RAW_DIR": "/data/raw",
        "PYTHONUNBUFFERED": "1",
    }


def test_backoffice_is_bounded_hardened_and_health_checked(backoffice):
    assert backoffice["restart"] == "unless-stopped"
    assert backoffice["mem_limit"] == "256m"
    assert backoffice["security_opt"] == ["no-new-privileges:true"]
    assert backoffice["logging"] == {
        "driver": "json-file", "options": {"max-size": "10m", "max-file": "3"},
    }
    check = backoffice["healthcheck"]
    assert check["test"][0] == "CMD" and "http://127.0.0.1:8080/healthz" in check["test"][-1]
    assert set(backoffice) == {
        "build", "image", "container_name", "command", "restart", "mem_limit",
        "security_opt", "logging", "networks", "ports", "volumes", "environment",
        "healthcheck", "read_only", "tmpfs", "cap_drop",
    }


def test_backoffice_root_filesystem_is_read_only_with_a_tmpfs(backoffice):
    assert backoffice["read_only"] is True
    assert backoffice["tmpfs"] == ["/tmp"]


def test_backoffice_drops_every_capability(backoffice):
    assert backoffice["cap_drop"] == ["ALL"]
    assert "cap_add" not in backoffice
    assert "privileged" not in backoffice


def test_backoffice_has_its_own_plain_bridge_not_the_proxy_network(backoffice_document,
                                                                   backoffice):
    """Not t2_proxy: Traefik and every container on it could reach :8080 regardless of the
    host-port bind. A plain user-defined bridge still publishes ports; `internal: true` would
    NOT (Docker sets up no port publishing for a container attached only to internal
    networks), so it is deliberately absent and the Tailscale-only port bind stays the
    perimeter."""
    assert backoffice["networks"] == ["prumo_backoffice"]
    assert backoffice_document["networks"] == {
        "prumo_backoffice": {"name": "prumo_backoffice", "driver": "bridge"},
    }
    assert "internal" not in backoffice_document["networks"]["prumo_backoffice"]
    assert backoffice["ports"] == ["100.118.19.6:8089:8080"]


def test_backoffice_runs_as_root_because_raw_evidence_is_owner_only(backoffice, tmp_path):
    """No `user:`. The worker (root) writes raw evidence through tempfile.mkstemp, which
    creates files mode 0600, so a non-root uid could not read them and the replay page would
    break. Root without capabilities (cap_drop ALL: no DAC override) on a read-only rootfs
    and a :ro data mount reads only what root owns. If RawStore ever writes 0644, revisit
    (user "1000:1000" plus a one-off chmod -R a+rX of the raw store)."""
    from ingest.rawstore import RawStore
    _sha, path = RawStore(tmp_path).save("src", b"payload")
    assert path.stat().st_mode & 0o777 == 0o600
    assert "user" not in backoffice


def test_backoffice_code_makes_no_network_calls():
    """Why the resolv.conf mount is gone: nothing in backoffice/ imports a network client,
    and the replay path (ingest.verify.replay_check + verifier constructors) is offline."""
    network = re.compile(r"^\s*(import|from)\s+(requests|urllib\.request|http\.client|socket|httpx|"
                         r"aiohttp|ingest\.http)\b", re.MULTILINE)
    for f in (REPO / "backoffice").rglob("*.py"):
        assert not network.search(f.read_text(encoding="utf-8")), f


def test_operator_runbook_documents_the_backoffice():
    text = OPERATIONS.read_text(encoding="utf-8")
    assert "## Backoffice" in text
    assert "http://100.118.19.6:8089" in text
    assert 'dc-web-up prumo-backoffice' in text
