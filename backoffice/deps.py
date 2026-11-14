"""Where the backoffice finds its inputs: the same environment contract as the worker."""
import os
from pathlib import Path

DEFAULT_DB = "/data/prumo.sqlite3"  # the scheduler's default (ingest/scheduler.py)
DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "registry" / "core.yaml"


def paths_from_env() -> tuple[Path, Path]:
    """(database, registry) from PRUMO_DB_PATH / PRUMO_REGISTRY, else the defaults."""
    return (Path(os.environ.get("PRUMO_DB_PATH") or DEFAULT_DB),
            Path(os.environ.get("PRUMO_REGISTRY") or DEFAULT_REGISTRY))
