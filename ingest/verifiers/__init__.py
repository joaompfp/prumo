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
# Modules that give dynamic import / introspection / direct DB access; rejected in any import
# form and as names. ingest.db and sqlite3: a verifier must not read expected values from the DB.
_DENY_MODULES = frozenset({"importlib", "builtins", "runpy", "pkgutil", "sys", "sqlite3"})
_DENY_NAMES = frozenset({"__import__", "exec", "eval", "compile", "vars", "globals", "locals",
                         "__builtins__"})
_DENY_ATTRS = frozenset({"__import__", "__builtins__"})


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

    (a) The module defining the verifier's class (whole AST, relative imports resolved):
        - imports from the `ingest` package only as `from ingest.<module> import <names>`; any
          plain `import ingest...` (aliased or not) is rejected, so the name `ingest` is never
          bound; `from ingest import sources|db|*` and importing a name `ingest` are rejected;
        - from `ingest.sources` only `Source` / `RawResponse`; never `ingest.sources.<x>`;
        - no attribute chain resolving (through import aliases) to `ingest.sources.<x>`, and
          no `.sources` on a name bound to the ingest package;
        - no import of or reference to importlib, builtins, runpy, pkgutil, sys, sqlite3 or
          ingest.db (any alias form, including importing those names from another module), no
          use of __import__, exec, eval, compile, vars, globals, locals, __builtins__;
        - no import whose dotted name has a component equal to the source name
          (case-insensitive; `ingest.verifiers.*` excepted).
    (b) The `ingest.*` modules the verifier module reaches transitively and those the parser
        module `ingest/sources/<source_name>.py` reaches (followed through their source files,
        not executed; descent stops at SHARED_ALLOWED) must not share anything outside
        SHARED_ALLOWED: a helper used by both parser and verifier is shared parsing code.

    Still undetectable: non-`ingest` helper modules (local or third-party) are not followed, and
    code constructed at runtime beyond the denylist (e.g. getattr with computed strings on an
    object that leads to a module) cannot be seen statically. Each adapter task therefore also
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
    aliases: dict[str, str] = {}  # name bound in the module -> dotted thing it refers to

    def named_like_source(dotted: str) -> bool:
        return (src in dotted.lower().split(".")) and not dotted.startswith("ingest.verifiers")

    def denied_module(dotted: str) -> bool:
        return (dotted.split(".")[0] in _DENY_MODULES
                or dotted == "ingest.db" or dotted.startswith("ingest.db."))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]  # `import a.b` binds `a`; `import a.b as c` binds c
                aliases[a.asname or top] = a.name if a.asname else top
                if a.name == "ingest" or a.name.startswith("ingest."):
                    bad.add(f"plain import binds 'ingest': import {a.name}")
                if denied_module(a.name):
                    bad.add(f"dynamic import/DB access: import {a.name}")
                if named_like_source(a.name):
                    bad.add(f"source-named import: {a.name}")
        elif isinstance(node, ast.ImportFrom):
            base = _resolve(node, package)
            for a in node.names:
                full = f"{base}.{a.name}"
                aliases[a.asname or a.name] = "ingest" if a.name == "ingest" else full
                if base.startswith("ingest.sources.") or (
                        base == "ingest.sources" and a.name not in _SOURCES_BASE_NAMES):
                    bad.add(f"collector import: from {base} import {a.name}")
                elif base == "ingest" and a.name in ("sources", "*"):
                    bad.add(f"collector import: from ingest import {a.name}")
                if a.name == "ingest":
                    bad.add(f"name binds 'ingest': from {base} import ingest")
                if denied_module(base) or denied_module(full if base == "ingest" else a.name):
                    bad.add(f"dynamic import/DB access: from {base} import {a.name}")
                if a.name in _DENY_NAMES:
                    bad.add(f"dynamic code: from {base} import {a.name}")
                if named_like_source(base) or named_like_source(full):
                    bad.add(f"source-named import: {full}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id in _DENY_NAMES or node.id in _DENY_MODULES:
                bad.add(f"dynamic code: {node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr in _DENY_ATTRS:
                bad.add(f"dynamic code: .{node.attr}")
            dotted = _dotted(node, aliases)
            if dotted is None:
                continue
            if dotted.startswith("ingest.sources."):
                rest = dotted[len("ingest.sources."):].split(".")[0]
                if rest not in _SOURCES_BASE_NAMES:
                    bad.add(f"attribute access to collector: {dotted}")
            elif dotted == "ingest.sources":
                bad.add("attribute access to collector: ingest.sources")
            if denied_module(dotted):
                bad.add(f"dynamic import/DB access: {dotted}")
    return sorted(bad)


def _dotted(node: ast.Attribute, aliases: dict[str, str]) -> str | None:
    """`a.b.c` with the root name resolved through the module's import aliases (an unbound root
    named `ingest` is taken literally); None if the chain is not rooted at a plain name."""
    parts = []
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return None
    root = aliases.get(cur.id, cur.id)
    return ".".join([root, *reversed(parts)])


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
