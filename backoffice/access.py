"""Admin access policy: explicit local development or a trusted proxy boundary.

The public Admin entry is served by Traefik behind Authelia. Neither an SNAT address nor a
`Remote-User` header proves anything on its own: a direct request to the tailnet port could
claim any identity. Proxy mode therefore requires a shared secret injected by Traefik after
Authelia succeeds, compares it in constant time, and only then accepts the allow-listed
`Remote-User`. An incomplete proxy configuration refuses to start rather than falling back
to local mode.

Local development is an explicit policy (`AccessPolicy.local()`), never an environment
default that a public deployment can inherit by accident. `create_app` takes the policy as
a parameter; only `app_from_env` reads the environment.
"""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hmac import compare_digest
from urllib.parse import urlsplit

ADMIN_PREFIX = "/dados/admin"
PROXY_SECRET_HEADER = "X-Prumo-Proxy-Secret"
IDENTITY_HEADER = "Remote-User"
LOCAL_ACTOR = "local-developer"
DEFAULT_USER = "joao"
DEFAULT_ORIGIN = "https://joao.date"
MIN_SECRET_CHARS = 32

_USER = re.compile(r"[A-Za-z0-9._@-]{1,64}\Z")
_HOST = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z")
_SECRET = re.compile(r"[A-Za-z0-9_-]{32,}\Z")


class AccessConfigError(RuntimeError):
    """Proxy access was requested but its configuration is incomplete or unsafe."""


class AccessDenied(RuntimeError):
    """The request did not prove the proxy identity; the response stays generic."""


def _canonical_https_origin(value: str) -> tuple[str, str]:
    """Validate `https://host[:443]` and return (origin, netloc), both canonical and lower.

    A scheme other than https, credentials, a path other than '/', a query, a fragment or a
    non-default port is refused: the configured origin is an exact boundary, not a prefix.
    """
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise AccessConfigError("PRUMO_ADMIN_ORIGIN is not a valid URL") from None
    if parts.scheme.lower() != "https":
        raise AccessConfigError("PRUMO_ADMIN_ORIGIN must use https")
    if parts.username or parts.password:
        raise AccessConfigError("PRUMO_ADMIN_ORIGIN must not carry credentials")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise AccessConfigError(
            "PRUMO_ADMIN_ORIGIN must be an origin only, with no path, query or fragment")
    if port not in (None, 443):
        raise AccessConfigError("PRUMO_ADMIN_ORIGIN must use port 443")
    host = (parts.hostname or "").lower()
    if not host or not _HOST.fullmatch(host):
        raise AccessConfigError("PRUMO_ADMIN_ORIGIN must name a plain host")
    return f"https://{host}", host


def _users(value: str) -> tuple[str, ...]:
    names = tuple(n.strip() for n in value.split(",") if n.strip())
    if not names or any(not _USER.fullmatch(n) for n in names):
        raise AccessConfigError(
            "PRUMO_ADMIN_USER must be a comma-separated list of simple usernames")
    return names


@dataclass(frozen=True)
class ProxyAccess:
    """The verified proxy boundary: shared secret, allow-listed users, canonical origin.

    The secret alphabet is `[A-Za-z0-9_-]` with at least 32 characters. The Traefik template
    places the value in a single-quoted YAML scalar, which cannot represent a quote; rejecting
    the unsupported characters here keeps an invalid value from ever reaching the edge.
    """

    secret: str
    users: tuple[str, ...]
    origin: str
    netloc: str

    @classmethod
    def create(cls, secret: str, user: str = DEFAULT_USER,
               origin: str = DEFAULT_ORIGIN) -> ProxyAccess:
        if not _SECRET.fullmatch(secret):
            raise AccessConfigError(
                f"PRUMO_ADMIN_PROXY_SECRET must be at least {MIN_SECRET_CHARS} characters "
                "using only A-Z, a-z, 0-9, '_' or '-' (for example `openssl rand -hex 32`); "
                "the Traefik template quotes it in YAML and cannot carry a quote")
        canonical, netloc = _canonical_https_origin(origin)
        return cls(secret=secret, users=_users(user), origin=canonical, netloc=netloc)

    def authenticate(self, request) -> str:
        """Return the verified user or raise AccessDenied. The secret check is constant time
        even when the header is absent, and every failure answers the same generic response."""
        offered = request.headers.get(PROXY_SECRET_HEADER) or ""
        if not compare_digest(offered.encode("utf-8"), self.secret.encode("utf-8")):
            raise AccessDenied
        host = (request.headers.get("host") or "").strip().lower()
        if host != self.netloc:
            raise AccessDenied
        user = request.headers.get(IDENTITY_HEADER) or ""
        if user not in self.users:
            raise AccessDenied
        return user

    def origin_allowed(self, request) -> bool:
        """CSRF in proxy mode: the configured canonical HTTPS origin, plus a matching Host.

        `request.url.scheme` is deliberately not consulted. Uvicorn may rebuild it from a
        forwarded header, so trusting it here would let `X-Forwarded-Proto` authorize a form.
        """
        site = (request.headers.get("sec-fetch-site") or "").strip().lower()
        if site and site not in ("same-origin", "none"):
            return False
        origin = request.headers.get("origin")
        if not origin:
            return False
        try:
            canonical, _ = _canonical_https_origin(origin)
        except AccessConfigError:
            return False
        if canonical != self.origin:
            return False
        host = (request.headers.get("host") or "").strip().lower()
        return host == self.netloc


@dataclass(frozen=True)
class AccessPolicy:
    """Local developer mode when `proxy` is None; trusted proxy mode otherwise."""

    proxy: ProxyAccess | None = None

    @classmethod
    def local(cls) -> AccessPolicy:
        return cls()

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AccessPolicy:
        """Build the production policy from the environment.

        No proxy variable set means local mode, which is what the shipped private service
        uses. A partially configured proxy is an error: setting the user or origin without
        the secret must not silently leave the public route unauthenticated.
        """
        env = os.environ if environ is None else environ
        secret = env.get("PRUMO_ADMIN_PROXY_SECRET") or ""
        user = (env.get("PRUMO_ADMIN_USER") or "").strip()
        origin = (env.get("PRUMO_ADMIN_ORIGIN") or "").strip()
        if not secret:
            if user or origin:
                raise AccessConfigError(
                    "PRUMO_ADMIN_PROXY_SECRET is required when proxy access is configured")
            return cls.local()
        return cls(ProxyAccess.create(secret, user or DEFAULT_USER, origin or DEFAULT_ORIGIN))

    def authenticate(self, request) -> str:
        if self.proxy is None:
            return LOCAL_ACTOR
        return self.proxy.authenticate(request)
