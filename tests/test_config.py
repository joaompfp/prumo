import importlib
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _reload_config(monkeypatch, env):
    """Reload app.config after applying environment overrides."""
    keys = [
        "CAE_DATA_DIR",
        "CAE_DB_PATH",
        "ANALYTICS_DB_PATH",
        "CAE_PORT",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    sys.modules.pop("app.config", None)
    import app.config as config

    return importlib.reload(config)


def test_defaults_to_repo_data_dir_when_no_env_and_no_data_mount(monkeypatch):
    monkeypatch.setattr(os.path, "isdir", lambda p: False if p == "/data" else os.path.isdir(p))

    config = _reload_config(monkeypatch, {})

    expected = REPO_ROOT / "data"
    assert Path(config.CAE_DB_PATH) == expected / "cae-data.duckdb"
    assert Path(config.ANALYTICS_DB_PATH) == expected / "analytics.db"


def test_uses_cae_data_dir_for_default_paths(monkeypatch, tmp_path):
    data_dir = tmp_path / "custom-data"

    config = _reload_config(monkeypatch, {"CAE_DATA_DIR": str(data_dir)})

    assert Path(config.CAE_DB_PATH) == data_dir / "cae-data.duckdb"
    assert Path(config.ANALYTICS_DB_PATH) == data_dir / "analytics.db"


def test_explicit_db_env_vars_take_precedence(monkeypatch, tmp_path):
    cae_db = tmp_path / "db" / "main.duckdb"
    analytics_db = tmp_path / "db" / "analytics.duckdb"

    config = _reload_config(
        monkeypatch,
        {
            "CAE_DATA_DIR": str(tmp_path / "ignored"),
            "CAE_DB_PATH": str(cae_db),
            "ANALYTICS_DB_PATH": str(analytics_db),
        },
    )

    assert Path(config.CAE_DB_PATH) == cae_db
    assert Path(config.ANALYTICS_DB_PATH) == analytics_db
