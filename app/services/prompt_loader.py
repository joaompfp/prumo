"""Load prompt templates from prompts/ directory with placeholder substitution."""
import os

_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts")
_cache: dict[str, str] = {}


def load_prompt(name: str, **kwargs) -> str:
    """Load prompts/<name>.txt and substitute {placeholders} with kwargs.

    Falls back to empty string if file not found (caller should handle).
    Templates use Python str.format_map() — use {{ and }} for literal braces.
    """
    if name not in _cache:
        path = os.path.join(_PROMPTS_DIR, f"{name}.txt")
        try:
            _cache[name] = open(path, encoding="utf-8").read()
        except FileNotFoundError:
            print(f"[prompt_loader] WARNING: {path} not found", flush=True)
            _cache[name] = ""
    template = _cache[name]
    if not template:
        return ""
    try:
        return template.format_map(kwargs) if kwargs else template
    except KeyError as e:
        print(f"[prompt_loader] WARNING: missing placeholder {e} in {name}.txt", flush=True)
        return template


def reload():
    """Clear cache — forces re-read from disk on next load_prompt() call."""
    _cache.clear()
