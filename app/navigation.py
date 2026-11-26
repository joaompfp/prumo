"""The public navigation contract, resolved once per request.

The template renders the links this module prepares; it never compares a path or a
mount prefix itself. A destination is `page` only when its href is the current
address, and `location` when the reader is on a nested route of that section. The
home link is therefore never current except on the home page itself.

The primary tasks rendered directly are `Catálogo`, `Comparações` and `Caderno`. The
themes, authored pages, sources and methodology sit in the supporting `Mais` disclosure,
so the compact rail keeps its task order. `/pesquisa` and `/caderno` already carry a task
search, so the shared header search is hidden across the catalogue section and on the
notebook instead of competing with it.

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
SEARCH_PATH = "/pesquisa"
CATALOGUE = (SEARCH_PATH, "Catálogo")
# The primary rail is the three reader tasks. `compact_label` is the shorter visible
# word used only in the narrow grid; the full label remains the desktop visible text.
SECTIONS = (("/comparar", "Comparações", "chart", "Comparar"),
            ("/caderno", None, "notebook", ""))
SUPPORT = (("/paginas", "Páginas"), ("/fontes", "Fontes"), ("/metodologia", "Metodologia"))
# These pages own a task-specific search; repeating the global one in the masthead
# would offer two term fields for the same job.
TASK_SEARCH_PATHS = frozenset({SEARCH_PATH, "/caderno"})
EXPLORE_LABEL = "Explorar"


@dataclass(frozen=True)
class NavLink:
    href: str
    label: str
    current: str = ""
    compact_label: str = ""
    icon: str = ""

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
    explore: NavDisclosure
    sections: tuple[NavLink, ...]
    support: NavDisclosure
    compact_current: str = ""
    compact_current_long: bool = False
    show_search: bool = True

    @property
    def search_href(self) -> str:
        return f"{self.base}{SEARCH_PATH}"

    @property
    def catalogue(self) -> NavLink:
        """The complete indicator catalogue, the first child of `Explorar`."""
        return self.explore.links[0]

    @property
    def themes(self) -> NavDisclosure:
        """The old themes-only disclosure, derived from the same `Explorar` links.

        Existing callers keep reading `themes`; the model keeps one authoritative
        tuple of theme links instead of preparing the same destinations twice.
        """
        links = self.explore.links[1:]
        current_label, state = _first_current(links)
        return NavDisclosure(label="Temas", links=links, current_label=current_label,
                             state=state)

    @property
    def primary(self) -> tuple[NavLink, ...]:
        """The three direct destinations: catalogue, comparisons and notebook."""
        return (self.catalogue, *self.sections)

    @property
    def more(self) -> NavDisclosure:
        """One `Mais` state over both themes and supporting pages.

        The panel renders the two groups separately, but its current marker and
        accessible context come from the same resolved link states as the rail.
        """
        links = (*self.themes.links, *self.support.links)
        current_label, state = _first_current(links)
        return NavDisclosure(label=self.support.label, links=links,
                             current_label=current_label, state=state)

    @property
    def destinations(self) -> tuple[NavLink, ...]:
        return (self.home, *self.explore.links, *self.sections, *self.support.links)


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


def _link(base: str, path: str, label: str, current_path: str, *,
          icon: str = "", compact_label: str = "") -> NavLink:
    if current_path == path:
        current = "page"
    elif current_path.startswith(path + "/"):
        current = "location"
    else:
        current = ""
    return NavLink(href=_href(base, path), label=label, current=current,
                   compact_label=compact_label, icon=icon)


def _first_current(links: tuple[NavLink, ...]) -> tuple[str, str]:
    link = next((link for link in links if link.current), None)
    return (link.label, link.current) if link else ("", "")


def build_navigation(path: str, base: str = "", notebook_label: str = "Caderno") -> Navigation:
    """Prepare every destination, its exact current state and the compact context."""
    current_path = _normalise(path)
    base = "" if base == "/" else base.rstrip("/")

    home = _link(base, HOME[0], HOME[1], current_path, icon="home")
    catalogue = _link(base, CATALOGUE[0], CATALOGUE[1], current_path, icon="list")
    themes = tuple(_link(base, href, label, current_path) for href, label in THEMES)
    sections = tuple(_link(base, href, label or notebook_label, current_path,
                           icon=icon, compact_label=compact_label)
                     for href, label, icon, compact_label in SECTIONS)
    support = tuple(_link(base, href, label, current_path) for href, label in SUPPORT)

    theme_current, theme_state = _first_current(themes)
    support_current, support_state = _first_current(support)

    # `Explorar` owns the catalogue first and the themes after it. Its state is the
    # strongest child state: an exact child page is `page`, a nested child `location`.
    explore_state = catalogue.current or theme_state
    explore_current = catalogue.label if catalogue.current else theme_current
    explore = NavDisclosure(label=EXPLORE_LABEL, links=(catalogue, *themes),
                            current_label=explore_current, state=explore_state)

    compact_current = home.label if home.current else ""
    if not compact_current and explore.current:
        compact_current = explore_current or explore.label
    if not compact_current:
        compact_current = next((link.label for link in (*sections, *support)
                                if link.current), "")

    return Navigation(
        base=base,
        home=home,
        explore=explore,
        sections=sections,
        support=NavDisclosure(label="Mais", links=support, current_label=support_current,
                              state=support_state),
        compact_current=compact_current,
        # Retained for callers that still read the compact context. The app bar
        # now marks the current destination itself.
        compact_current_long=len(compact_current) >= 10,
        # The catalogue owns its search on `/pesquisa` and on every nested catalogue
        # view; the notebook owns its own task search on `/caderno`.
        show_search=not (current_path in TASK_SEARCH_PATHS
                         or current_path.startswith(SEARCH_PATH + "/")),
    )


def legacy_links(notebook_label: str = "Caderno") -> tuple[tuple[str, str], ...]:
    """The flat `(href, label)` shape the backoffice preview still passes around."""
    return ((HOME, CATALOGUE, *THEMES,
             *((href, label or notebook_label) for href, label, _, _ in SECTIONS), *SUPPORT))


__all__ = ["NavDisclosure", "NavLink", "Navigation", "build_navigation",
           "request_path", "root_path_base", "legacy_links"]
