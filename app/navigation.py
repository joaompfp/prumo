"""The public navigation contract, resolved once per request.

The template renders the links this module prepares; it never compares a path or a
mount prefix itself. A destination is `page` only when its href is the current
address, and `location` when the reader is on a nested route of that section. The
home link is therefore never current except on the home page itself.

`X-Forwarded-Prefix` remains the edge mount contract. A real ASGI `root_path` mount
is honoured as the fallback when the edge did not forward a prefix. `root_path`
comes from the server configuration, not from a request header, so it is only
normalised here instead of being validated like the forwarded header.
"""
from dataclasses import dataclass

from starlette.requests import Request

HOME = ("/", "Início")
THEMES = (("/temas/economy", "Economia"),
          ("/temas/demography", "Demografia"),
          ("/temas/energy", "Energia"))
SECTIONS = (("/comparar", "Comparações"), ("/caderno", None), ("/paginas", "Páginas"))
SUPPORT = (("/fontes", "Fontes"), ("/metodologia", "Metodologia"))
SEARCH_PATH = "/pesquisa"


@dataclass(frozen=True)
class NavLink:
    href: str
    label: str
    current: str = ""

    @property
    def is_current(self) -> bool:
        return self.current == "page"


@dataclass(frozen=True)
class NavDisclosure:
    label: str
    links: tuple[NavLink, ...]
    current_label: str = ""
    state: str = ""

    @property
    def current(self) -> bool:
        return bool(self.state)


@dataclass(frozen=True)
class Navigation:
    base: str
    home: NavLink
    themes: NavDisclosure
    sections: tuple[NavLink, ...]
    support: NavDisclosure
    compact_current: str = ""
    compact_current_long: bool = False

    @property
    def search_href(self) -> str:
        return f"{self.base}{SEARCH_PATH}"

    @property
    def destinations(self) -> tuple[NavLink, ...]:
        return (self.home, *self.themes.links, *self.sections, *self.support.links)


def root_path_base(request: Request) -> str:
    """The server-configured root path, normalised, or '' when it is not a plain path."""
    root = str(request.scope.get("root_path") or "").rstrip("/")
    if root.startswith("/") and "\\" not in root and "//" not in root:
        return root
    return ""


def request_path(request: Request) -> str:
    """The application path, without a real mount's root path when the server kept it.

    A `root_path` parameter leaves the path alone, while a mounted ASGI app may carry
    the mount at the front of `scope["path"]`. Stripping only the known root path keeps
    an X-Forwarded-Prefix address, which never includes the prefix, unchanged.
    """
    path = request.url.path or "/"
    root = str(request.scope.get("root_path") or "").rstrip("/")
    if root and path.startswith(root + "/"):
        return _normalise(path[len(root):])
    if root and path == root:
        return "/"
    return _normalise(path)


def _normalise(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/") or "/"


def _href(base: str, path: str) -> str:
    return f"{base}/" if path == "/" else f"{base}{path}"


def _link(base: str, path: str, label: str, current_path: str) -> NavLink:
    if current_path == path:
        current = "page"
    elif current_path.startswith(path + "/"):
        current = "location"
    else:
        current = ""
    return NavLink(href=_href(base, path), label=label, current=current)


def build_navigation(path: str, base: str = "", notebook_label: str = "Caderno") -> Navigation:
    """Prepare every destination, its exact current state and the compact context."""
    current_path = _normalise(path)
    base = "" if base == "/" else base.rstrip("/")

    home = _link(base, HOME[0], HOME[1], current_path)
    themes = tuple(_link(base, href, label, current_path) for href, label in THEMES)
    sections = tuple(_link(base, href, label or notebook_label, current_path)
                     for href, label in SECTIONS)
    support = tuple(_link(base, href, label, current_path) for href, label in SUPPORT)

    theme_current = next((link.label for link in themes if link.current), "")
    theme_state = next((link.current for link in themes if link.current), "")
    support_current = next((link.label for link in support if link.current), "")
    support_state = next((link.current for link in support if link.current), "")
    compact_current = home.label if home.current else theme_current
    if not compact_current:
        compact_current = next((link.label for link in (*sections, *support)
                                if link.current), "")

    return Navigation(
        base=base,
        home=home,
        themes=NavDisclosure(label="Temas", links=themes, current_label=theme_current,
                             state=theme_state),
        sections=sections,
        support=NavDisclosure(label="Mais", links=support, current_label=support_current,
                              state=support_state),
        compact_current=compact_current,
        # Long labels may not share the compact summary line at 320px. The template
        # only tags them; the narrow media query moves that one label to a second line.
        compact_current_long=len(compact_current) >= 10,
    )


def legacy_links(notebook_label: str = "Caderno") -> tuple[tuple[str, str], ...]:
    """The flat `(href, label)` shape the backoffice preview still passes around."""
    return ((HOME, *THEMES, *((href, label or notebook_label) for href, label in SECTIONS),
             *SUPPORT))


__all__ = ["NavDisclosure", "NavLink", "Navigation", "build_navigation",
           "request_path", "root_path_base", "legacy_links"]
