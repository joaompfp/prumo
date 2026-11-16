"""Where the backoffice finds its inputs: the same environment contract as the worker."""
import os
from pathlib import Path

DEFAULT_DB = "/data/prumo.sqlite3"  # the scheduler's default (ingest/scheduler.py)
DEFAULT_RAW = "/data/raw"           # the scheduler's default raw evidence store
DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "registry" / "core.yaml"
LANG = "pt"  # the language the backoffice renders reader text in (presentation package)


def paths_from_env() -> tuple[Path, Path, Path]:
    """(database, registry, raw store) from PRUMO_DB_PATH / PRUMO_REGISTRY / PRUMO_RAW_DIR,
    else the defaults."""
    return (Path(os.environ.get("PRUMO_DB_PATH") or DEFAULT_DB),
            Path(os.environ.get("PRUMO_REGISTRY") or DEFAULT_REGISTRY),
            Path(os.environ.get("PRUMO_RAW_DIR") or DEFAULT_RAW))


# Host headers the app answers (DNS-rebinding guard): f0nix's Tailscale address plus the
# loopback names the container healthcheck uses. Add a MagicDNS name through the env var.
DEFAULT_ALLOWED_HOSTS = ["100.118.19.6", "localhost", "127.0.0.1"]


def allowed_hosts_from_env() -> list[str]:
    """PRUMO_BACKOFFICE_ALLOWED_HOSTS (comma-separated host names, no ports), else the
    defaults."""
    raw = os.environ.get("PRUMO_BACKOFFICE_ALLOWED_HOSTS", "")
    hosts = [h.strip() for h in raw.split(",") if h.strip()]
    return hosts or list(DEFAULT_ALLOWED_HOSTS)


def editorial_path_from_env() -> Path | None:
    """The writable database for the editorial editor (PRUMO_EDITORIAL_DB, mounted :rw).

    Unset means the editor is unavailable and every other page keeps working: a read-only
    deployment must stay a valid deployment.
    """
    raw = os.environ.get("PRUMO_EDITORIAL_DB", "").strip()
    return Path(raw) if raw else None
