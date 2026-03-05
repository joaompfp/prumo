import json
import os


def _default_data_dir() -> str:
    """Pick a writable data directory for non-container runs.

    Preference order:
    1) CAE_DATA_DIR env var
    2) /data (container default)
    3) <repo>/data (local standalone default)
    """
    if os.environ.get("CAE_DATA_DIR"):
        return os.environ["CAE_DATA_DIR"]
    if os.path.isdir("/data"):
        return "/data"
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# ── Site config (editable without rebuild) ────────────────────────────
# Loaded first so paths.db can override CAE_DB_PATH default.
_CAE_DB_PATH_ENV = os.environ.get("CAE_DB_PATH")
_DATA_DIR_DEFAULT = os.path.dirname(_CAE_DB_PATH_ENV) if _CAE_DB_PATH_ENV else _default_data_dir()
_SITE_CONFIG_PATH = os.path.join(_DATA_DIR_DEFAULT, "site.json")
_SITE_CFG = {}
try:
    if os.path.exists(_SITE_CONFIG_PATH):
        with open(_SITE_CONFIG_PATH, encoding="utf-8") as f:
            _SITE_CFG = json.load(f)
except Exception:
    _SITE_CFG = {}

_paths = _SITE_CFG.get("paths", {})


def site_cfg(key: str, default=None):
    """Read from site.json, fall back to env var CAE_<KEY>, then default."""
    if key in _SITE_CFG:
        return _SITE_CFG[key]
    env_key = "CAE_" + key.upper()
    return os.environ.get(env_key, default)


# ── Paths (site.json > env var > default) ────────────────────────────
CAE_DB_PATH = _paths.get("db") or _CAE_DB_PATH_ENV or os.path.join(_DATA_DIR_DEFAULT, "cae-data.duckdb")
ENERGY_DB_PATH = os.path.join(os.path.dirname(CAE_DB_PATH), "energy-data.db")
ANALYTICS_DB_PATH = _paths.get("analytics_db") or os.environ.get("ANALYTICS_DB_PATH") or os.path.join(_DATA_DIR_DEFAULT, "analytics.db")
IDEOLOGIES_DIR = _paths.get("ideologies_dir") or os.path.join(os.path.dirname(CAE_DB_PATH), "ideologies")
INTERPRET_CACHE_PATH = _paths.get("interpret_cache") or os.path.join(os.path.dirname(CAE_DB_PATH), "interpret-cache.json")
PAINEL_CACHE_PATH = _paths.get("painel_cache") or os.path.join(os.path.dirname(CAE_DB_PATH), "painel-analysis-cache.json")

PORT = int(os.environ.get("CAE_PORT", "8080"))
BASE_PATH = os.environ.get("CAE_BASE_PATH", "").rstrip("/")
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

ENERGY_SOURCES = {"DGEG", "ERSE"}

SKILLS_DIR = os.environ.get(
    "SKILLS_DIR",
    "/home/node/.openclaw/workspace/skills/cae-reports"
)

# ── Lens / ideology config ───────────────────────────────────────────
CUSTOM_LENS_DEFAULT = site_cfg("custom_lens_default", "")

# ── Output language ──────────────────────────────────────────────────
# Map of language codes → language descriptions for model prompts
OUTPUT_LANGUAGES: dict = site_cfg("output_languages", {
    "pt": "português europeu (sem brasileirismos)",
})
DEFAULT_OUTPUT_LANGUAGE: str = site_cfg("default_output_language", "pt")
