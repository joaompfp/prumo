"""Independent verifier contract (spec 6b). One verifier per source (Tasks 9-16) implements
`Verifier`; it re-reads sampled observations through a channel different from the collector's
(another endpoint or format, the publisher's web table, a downloadable file) and must not reuse the
collector's parser. Verifiers are blinded: they get only the key and the registry spec of each
sampled observation (`BlindItem`), never the stored value, unit or flag; `ingest.verify` compares.
`register_verifier` enforces the independence rule (Ruling Q) on the verifier's module.
"""
import ast
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import ingest
from ingest.http import Http
from ingest.models import SeriesSpec

_INGEST_ROOT = Path(ingest.__file__).parent  # module files are resolved here, never executed
_REGISTRY: dict[str, "Verifier"] = {}

# Shared infrastructure a verifier and its source's parser may both depend on. The root package
# `ingest` (an empty __init__) is necessarily imported by both.
SHARED_ALLOWED = frozenset({"ingest", "ingest.models", "ingest.http", "ingest.sources",
                            "ingest.verifiers", "ingest.rawstore"})
_SOURCES_BASE_NAMES = frozenset({"Source", "RawResponse"})
_DYNAMIC_NAMES = frozenset({"importlib", "__import__", "exec", "eval"})


@dataclass(frozen=True)
class BlindItem:
    """What a verifier is asked to look up: a key and its registry spec. Deliberately carries no
    expected value, unit or flag (spec.unit is the registry's declared unit, not the stored one)."""
    series_id: str
    period: str  # canonical period
    spec: SeriesSpec


@dataclass(frozen=True)
class ItemResult:
    """What the independent channel shows for one BlindItem.

    series_id / period: the key this result is for; must equal the item at the same position.
    observed_text: the publisher's number as shown there, None = not found (a mismatch).
    evidence_url: where it was read (URL incl. query, or file URL + locator).
    observed_decimal: decimal separator of observed_text.
    observed_unit / observed_flag: None = this channel does not expose them (not compared).
    evidence: optional bytes the value was read from (page, file, JSON); stored in the raw
        store by verify_run so an auditor sees exactly what the verifier saw.
    """
    series_id: str
    period: str
    observed_text: str | None
    evidence_url: str
    observed_decimal: Literal[".", ","] = "."
    observed_unit: str | None = None
    observed_flag: str | None = None
    evidence: bytes | None = None


class Verifier(Protocol):
    """source_name: the registry source this verifier checks.
    check: one ItemResult per item, same length and order; may raise (counted as a failure)."""
    source_name: str

    def check(self, items: list[BlindItem], http: Http) -> list[ItemResult]: ...


def register_verifier(verifier: Verifier) -> None:
    """Register the verifier of `verifier.source_name` (ValueError if already registered or if
    the independence rule fails).

    (a) The module defining the verifier's class (whole AST, relative imports resolved) must not
        import `ingest` or `ingest.sources` bare, `from ingest import sources`, any
        `ingest.sources.<submodule>`, any module with a dotted-name component equal to the source
        name (case-insensitive; `ingest.verifiers.*` excepted), nor use importlib, __import__,
        exec, eval or sys.modules. From `ingest.sources` only `Source` / `RawResponse` may be
        imported.
    (b) The `ingest.*` modules the verifier module reaches transitively and those the parser
        module `ingest/sources/<source_name>.py` reaches (followed through their source files,
        not executed; descent stops at SHARED_ALLOWED) must not share anything outside
        SHARED_ALLOWED: a helper used by both parser and verifier is shared parsing code.

    Limits: dynamic code outside these patterns (getattr on a module, code built at runtime) and
    non-`ingest` third-party/local helpers are not followed; each adapter task additionally
    carries a subprocess independence test.
    """
    name = verifier.source_name
    if name in _REGISTRY:
        raise ValueError(f"a verifier for source {name!r} is already registered")
    module = sys.modules.get(type(verifier).__module__)
    path = inspect.getsourcefile(module) if module is not None else None
    if path is None:
        raise ValueError(f"cannot inspect {type(verifier).__module__!r} (no source file)")
    tree = _parse(Path(path))
    package = module.__package__ or ""
    bad = _direct_violations(tree, package, name)
    if bad:
        raise ValueError(f"verifier for {name!r} must be independent of the collector, but its "
                         f"module imports/uses {bad}")
    parser = _module_file(f"ingest.sources.{name}")
    if parser is not None:
        shared = (_closure(_ingest_imports(tree, package))
                  & _closure({f"ingest.sources.{name}"})) - SHARED_ALLOWED
        if shared:
            raise ValueError(f"verifier for {name!r} shares code with its parser through "
                             f"imports of {sorted(shared)}")
    _REGISTRY[name] = verifier


def get_verifier(source_name: str) -> Verifier:
    """The registered verifier of `source_name` (KeyError if none)."""
    return _REGISTRY[source_name]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _resolve(node: ast.ImportFrom, package: str) -> str:
    if not node.level:
        return node.module or ""
    parts = package.split(".") if package else []
    if node.level - 1 > len(parts) or (node.level > 1 and not parts):
        raise ValueError(f"cannot resolve relative import (level {node.level}) in {package!r}")
    base = parts[:len(parts) - (node.level - 1)]
    return ".".join(base + ([node.module] if node.module else []))


def _imported_names(tree: ast.Module, package: str) -> list[tuple[str, str | None]]:
    """(module, imported name or None) for every import statement in the tree."""
    out: list[tuple[str, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(a.name, None) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = _resolve(node, package)
            out += [(base, a.name) for a in node.names]
    return out


def _direct_violations(tree: ast.Module, package: str, source_name: str) -> list[str]:
    bad: set[str] = set()
    src = source_name.lower()

    def named_like_source(dotted: str) -> bool:
        return (src in dotted.lower().split(".")) and not dotted.startswith("ingest.verifiers")

    for module, name in _imported_names(tree, package):
        full = f"{module}.{name}" if name else module
        if name is None and module in ("ingest", "ingest.sources"):
            bad.add(f"import {module}")
        elif module.startswith("ingest.sources."):
            bad.add(module)
        elif module == "ingest" and name in ("sources", "*"):
            bad.add(f"from ingest import {name}")
        elif module == "ingest.sources" and name not in _SOURCES_BASE_NAMES:
            bad.add(full)
        elif named_like_source(module) or (name and named_like_source(full)):
            bad.add(full)
        if module.split(".")[0] in _DYNAMIC_NAMES or (module == "sys" and name == "modules"):
            bad.add(full)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in _DYNAMIC_NAMES:
            bad.add(node.id)
        elif (isinstance(node, ast.Attribute) and node.attr == "modules"
              and isinstance(node.value, ast.Name) and node.value.id == "sys"):
            bad.add("sys.modules")
    return sorted(bad)


def _module_file(dotted: str) -> Path | None:
    """Source file of an `ingest.*` module under _INGEST_ROOT, or None."""
    parts = dotted.split(".")
    if parts[0] != "ingest":
        return None
    base = _INGEST_ROOT.joinpath(*parts[1:])
    for f in (base / "__init__.py", base.with_suffix(".py")):
        if f.is_file():
            return f
    return None


def _ingest_imports(tree: ast.Module, package: str) -> set[str]:
    """`ingest.*` modules (and their parent packages) imported by the tree."""
    found: set[str] = set()
    for module, name in _imported_names(tree, package):
        if module.split(".")[0] != "ingest":
            continue
        cands = [module] + ([f"{module}.{name}"] if name and name != "*" else [])
        for c in cands:
            if c == module or _module_file(c) is not None:
                parts = c.split(".")
                found |= {".".join(parts[:i]) for i in range(1, len(parts) + 1)}
    return found


def _closure(start: set[str]) -> set[str]:
    """Modules reachable from `start` through `ingest.*` imports; does not descend into
    SHARED_ALLOWED (vetted infrastructure)."""
    seen: set[str] = set()
    stack = list(start)
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        f = _module_file(m)
        if m in SHARED_ALLOWED or f is None:
            continue
        package = m if f.name == "__init__.py" else m.rpartition(".")[0]
        stack += _ingest_imports(_parse(f), package)
    return seen
