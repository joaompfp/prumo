"""Web-facing URL helpers shared by the public site and the backoffice.

The only piece of knowledge here is the mount prefix Traefik strips before the app sees a
request. It is validated once, here, instead of in every app: `//evil.example` would turn
every link into a protocol-relative link to another host, and a query, fragment, backslash
or `.`/`..` segment has no business in a prefix.
"""
import re

from starlette.requests import Request

_PREFIX = re.compile(r"/(?:[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*)?")


def mount_prefix(request: Request) -> str:
    """The mount prefix Traefik strips (`/dados`), normalised to '' or '/dados'.

    Anything that is not a plain path is ignored rather than echoed.
    """
    prefix = request.headers.get("x-forwarded-prefix", "").strip()
    if not prefix or "\\" in prefix or "//" in prefix:
        return ""
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    prefix = prefix.rstrip("/")
    if not _PREFIX.fullmatch(prefix):
        return ""
    if any(part in (".", "..") for part in prefix.split("/")):
        return ""
    return prefix


def prefixed(prefix: str, path: str) -> str:
    """Join a validated prefix with an absolute app path (query string allowed)."""
    if not path.startswith("/"):
        raise ValueError("path must start with '/'")
    return f"{prefix}{path}" if prefix else path
