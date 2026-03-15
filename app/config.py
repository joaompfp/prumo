import json
import os

# ── Site config: /data/site.json (editable without rebuild) ──────────
# Loaded first so paths.db can override CAE_DB_PATH default.
_DATA_DIR_DEFAULT = os.environ.get("CAE_DB_PATH", "/data/cae-data.duckdb")
_SITE_CONFIG_PATH = os.path.join(os.path.dirname(_DATA_DIR_DEFAULT), "site.json")
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
CAE_DB_PATH = os.environ.get("CAE_DB_PATH") or _paths.get("db") or "/data/cae-data.duckdb"
ENERGY_DB_PATH = os.path.join(os.path.dirname(CAE_DB_PATH), "energy-data.db")
ANALYTICS_DB_PATH = _paths.get("analytics_db") or os.environ.get("ANALYTICS_DB_PATH", "/data/analytics.db")
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
