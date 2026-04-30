"""
Ideology Lenses — runtime-selectable political perspectives for AI analysis.

Each lens is derived from the actual program of a Portuguese political party
(Programa Eleitoral) or from structured political axis frameworks. The source
document is cited in each lens definition.

Prompt text is loaded from /data/ideologies/<id>.txt at import time.
The CAE lens also falls back to /data/ideology.txt for backward compatibility.

Lens definitions and fallback prompts are loaded from JSON config files.
"""
import json
import os
from .interpret import _load_ideology
from ..config import site_cfg, IDEOLOGIES_DIR

_IDEOLOGIES_DIR = IDEOLOGIES_DIR
_HERE = os.path.dirname(os.path.dirname(__file__))  # app/

# Ideology file mapping from site.json (e.g. {"pcp": "pcp.txt", ...})
_IDEOLOGY_MAP: dict = site_cfg("ideologies", {}) or {}

# Default link sources
_DEFAULT_LINK_SOURCES = "publico.pt, dn.pt, rtp.pt, observador.pt, expresso.pt, eco.sapo.pt, jornaldenegocios.pt"


def _load_lens_file(lens_id: str) -> str | None:
    """Load ideology text from ideologies dir (configured in site.json paths.ideologies_dir).
    Filename comes from site.json 'ideologies' map, falling back to <lens_id>.txt."""
    filename = _IDEOLOGY_MAP.get(lens_id, f"{lens_id}.txt")
    path = os.path.join(_IDEOLOGIES_DIR, filename)
    try:
        if os.path.exists(path):
            text = open(path, encoding="utf-8").read().strip()
            if text:
                return text
    except Exception:
        pass
    return None


# ── Load lens definitions from JSON ────────────────────────────────
_constants_dir = os.path.join(_HERE, "constants")

with open(os.path.join(_constants_dir, "lenses.json"), encoding="utf-8") as _f:
    LENSES = json.load(_f)

# Add prompt=None to each lens (will be populated below)
for _lens in LENSES:
    _lens["prompt"] = None

with open(os.path.join(_constants_dir, "fallback_prompts.json"), encoding="utf-8") as _f:
    _FALLBACK_PROMPTS = json.load(_f)

# Index for fast lookup
_LENS_MAP = {lens["id"]: lens for lens in LENSES}

# ── Load all lens prompts from files at import time ────────────────
for lens in LENSES:
    lid = lens["id"]
    if lid == "custom":
        continue  # custom lens text is provided at runtime
    # Try file first, then hardcoded fallback
    file_text = _load_lens_file(lid)
    if file_text:
        lens["prompt"] = file_text
    elif lid == "cae":
        # CAE: fallback to legacy ideology.txt
        lens["prompt"] = _load_ideology()
    elif lid in _FALLBACK_PROMPTS:
        lens["prompt"] = _FALLBACK_PROMPTS[lid]

_loaded = sum(1 for l in LENSES if l.get("prompt"))
print(f"[ideology_lenses] Loaded {_loaded}/{len(LENSES)-1} lens prompts "
      f"(dir: {_IDEOLOGIES_DIR}, exists: {os.path.isdir(_IDEOLOGIES_DIR)})", flush=True)


def get_lenses() -> list:
    """Return all available lenses (without full prompt text, for the frontend)."""
    return [
        {
            "id": lens["id"],
            "label": lens["label"],
            "short": lens["short"],
            "party": lens["party"],
            "source": lens["source"],
            "color": lens["color"],
            "icon": lens.get("icon"),
        }
        for lens in LENSES
    ]


def get_lens_prompt(lens_id: str, custom_ideology: str = None) -> str:
    """Return the ideology prompt for a given lens ID.
    For lens_id='custom', returns the user-provided custom_ideology text.
    Falls back to CAE (operator's custom lens) if lens_id is invalid."""
    if lens_id == "custom" and custom_ideology:
        return custom_ideology.strip()
    lens = _LENS_MAP.get(lens_id)
    if lens and lens.get("prompt"):
        return lens["prompt"]
    # Default: operator's custom lens (ideology.txt)
    return _LENS_MAP.get("cae", {}).get("prompt") or _load_ideology()


def get_lens_metadata(lens_id: str) -> dict | None:
    """Return full lens metadata (for Metodologia display)."""
    return _LENS_MAP.get(lens_id)


def get_lens_link_sources(lens_id: str) -> str:
    """Return the preferred link sources string for a given lens."""
    lens = _LENS_MAP.get(lens_id)
    if lens and lens.get("link_sources"):
        return lens["link_sources"]
    return _DEFAULT_LINK_SOURCES
