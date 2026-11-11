"""Independent verifier contract (spec 6b). One verifier per source (Tasks 9-16) implements
`Verifier`; it re-reads sampled observations through a channel different from the collector's
(another endpoint or format, the publisher's web table, a downloadable file) and must not reuse the
collector's parser. Verifiers are blinded: they get only the key and the registry spec of each
sampled observation (`BlindItem`), never the stored value, unit or flag; `ingest.verify` compares.
`register_verifier` enforces the independence rule (Ruling Q) on the verifier's module.
"""
import ast
import importlib
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

# Ruling S: what a verifier module may import. Extending these is an explicit, reviewed change.
VERIFIER_INGEST_IMPORTS: dict[str, frozenset[str]] = {
    "ingest.http": frozenset({"HttpResult", "Http"}),
    # parse_number/parse_decimal for numeric comparison; normalize_period for verifiers whose
    # channel shows period labels (e.g. INE's 'Setembro de 2026') that must be pinned to the
    # canonical period read from the evidence, not echoed from the request.
    "ingest.models": frozenset({"parse_number", "SeriesSpec", "normalize_period"}),
    "ingest.rawstore": frozenset({"RawStore"}),
    "ingest.sources": frozenset({"Source", "RawResponse"}),
    "ingest.verifiers": frozenset({"ItemResult", "BlindItem", "Verifier"}),
}
VERIFIER_STDLIB_IMPORTS = frozenset({
    "__future__", "typing", "dataclasses", "decimal", "re", "json", "csv", "io", "gzip",
    "zipfile", "datetime", "urllib.parse", "collections", "itertools", "functools", "math",
    "html.parser", "xml.etree.ElementTree", "hashlib", "base64", "unicodedata", "enum", "logging"})
_FORBIDDEN_NAMES = frozenset({
    "__import__", "__builtins__", "__loader__", "__spec__", "__globals__", "exec", "eval",
    "compile", "vars", "globals", "locals", "getattr", "setattr", "delattr", "type", "super",
    "open"})
# Names that evaluate strings (typing evaluates string annotations with eval()) or resolve
# objects by name; rejected as bare names, as attributes and as imported names.
_EVALUATING_NAMES = frozenset({"get_type_hints", "ForwardRef", "_eval_type", "_evaluate",
                               "register", "evaluate", "resolve_name"})

# Shared infrastructure a verifier and its source's parser may both depend on: the allow-listed
# ingest modules plus the root package `ingest` (an empty __init__ both necessarily import).
SHARED_ALLOWED = frozenset({"ingest", *VERIFIER_INGEST_IMPORTS})
# Modules an attribute chain may pass through: the allowlists and their parent packages.
_REACHABLE_MODULES = frozenset(
    ".".join(m.split(".")[:i]) for m in VERIFIER_STDLIB_IMPORTS | SHARED_ALLOWED
    for i in range(1, len(m.split(".")) + 1))


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

    (a) Static allowlist check (Ruling S) on the module defining the verifier's class, whole
        AST (also imports inside functions, `if TYPE_CHECKING:` and `try:` blocks):
        - from `ingest`, only `from ingest.<module> import <names>` with module and names in
          VERIFIER_INGEST_IMPORTS; any plain `import ingest...`, `from ingest import x`, other
          modules or names (private ones included) are rejected;
        - other imports only from VERIFIER_STDLIB_IMPORTS (import or from-import); a name
          imported from them must not be a module or private;
        - no star imports and no relative imports from any module;
        - no attribute whose name starts with `__`, none of the bare names in
          _FORBIDDEN_NAMES (exec, eval, getattr, type, open, __import__, ...), none of the
          string-evaluating names in _EVALUATING_NAMES (get_type_hints, ForwardRef, register,
          resolve_name, ...) as name, attribute or import, no quoted (string-constant)
          annotation (unquoted ones, also under `from __future__ import annotations`, are
          fine), and no attribute chain on an imported name that reaches a module outside the
          allowlists (e.g. `logging.sys`);
        - no import whose dotted name has a component equal to the source name
          (case-insensitive).
    (b) The `ingest.*` modules the verifier module reaches transitively and those the parser
        module `ingest/sources/<source_name>.py` reaches (followed through their source files,
        not executed; descent stops at SHARED_ALLOWED) must not share anything outside
        SHARED_ALLOWED: a helper used by both parser and verifier is shared parsing code.

    This static check is lint: Python can reach code at runtime in ways no static rule
    enumerates, and non-`ingest` helper modules are not followed. The guarantee is the runtime
    test `ingest.verifiers.independence.assert_verifier_independent`, a subprocess that blocks
    the collector's modules by name and checks module names AND file origins (and files
    opened), which every adapter task must run. Neither can detect a verifier that embeds a
    re-implementation of the parser's logic; adapter reviewers must confirm the verifier reads
    the independent channel.
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
    bad = _static_violations(tree, name)
    if _module_file(f"ingest.sources.{name}") is not None:
        shared = (_closure(_ingest_imports(tree, package))
                  & _closure({f"ingest.sources.{name}"})) - SHARED_ALLOWED
        bad += [f"shares code with its parser: {m}" for m in sorted(shared)]
    if bad:
        raise ValueError(f"verifier for {name!r} must be independent of the collector: {bad}")
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


def _static_violations(tree: ast.Module, source_name: str) -> list[str]:
    bad: set[str] = set()
    src = source_name.lower()
    bound: dict[str, str] = {}  # name bound by an allowed import -> dotted object it names

    def named_like_source(dotted: str) -> None:
        if src in dotted.lower().split("."):
            bad.add(f"source-named import: {dotted}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                named_like_source(a.name)
                if a.name == "ingest" or a.name.startswith("ingest."):
                    bad.add(f"import not allowed (use 'from ingest.<module> import <name>'): "
                            f"import {a.name}")
                elif a.name not in VERIFIER_STDLIB_IMPORTS:
                    bad.add(f"module not in stdlib allowlist: import {a.name}")
                elif a.asname:
                    bound[a.asname] = a.name
                else:
                    top = a.name.split(".")[0]
                    bound[top] = top
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            stmt = f"from {'.' * node.level}{base} import {', '.join(a.name for a in node.names)}"
            named_like_source(base)
            if node.level:
                bad.add(f"relative import not allowed: {stmt}")
                continue
            if any(a.name == "*" for a in node.names):
                bad.add(f"star import not allowed: {stmt}")
                continue
            for a in node.names:
                named_like_source(f"{base}.{a.name}")
                full = f"{base}.{a.name}"
                if base == "ingest" or base.startswith("ingest."):
                    allowed = VERIFIER_INGEST_IMPORTS.get(base)
                    if allowed is None:
                        bad.add(f"ingest module not in allowlist: from {base} import {a.name}")
                    elif a.name not in allowed:
                        bad.add(f"name not in allowlist for {base}: {a.name}")
                    else:
                        bound[a.asname or a.name] = full
                elif base not in VERIFIER_STDLIB_IMPORTS:
                    bad.add(f"module not in stdlib allowlist: from {base} import {a.name}")
                elif a.name in _FORBIDDEN_NAMES | _EVALUATING_NAMES:
                    bad.add(f"forbidden name: from {base} import {a.name}")
                elif a.name.startswith("_"):
                    bad.add(f"private name not allowed: from {base} import {a.name}")
                elif (inspect.ismodule(getattr(importlib.import_module(base), a.name, None))
                      and full not in VERIFIER_STDLIB_IMPORTS):
                    bad.add(f"module not in stdlib allowlist: from {base} import {a.name}")
                else:
                    bound[a.asname or a.name] = full
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES | _EVALUATING_NAMES:
            bad.add(f"forbidden name: {node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                bad.add(f"dunder attribute: .{node.attr}")
            elif node.attr in _EVALUATING_NAMES:
                bad.add(f"forbidden attribute: .{node.attr}")
            else:
                reached = _module_reached(node, bound)
                if reached:
                    bad.add(f"attribute chain reaches module not in allowlist: {reached}")
        annotation = (node.annotation if isinstance(node, (ast.arg, ast.AnnAssign)) else
                      node.returns if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                      else None)
        if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
            bad.add(f"string annotation not allowed: {annotation.value!r}")
    return sorted(bad)


def _module_reached(node: ast.Attribute, bound: dict[str, str]) -> str | None:
    """Follow `name.a.b` from an allowed import (objects of already allow-listed modules) and
    return the name of the first module reached that is not allow-listed."""
    attrs = []
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        attrs.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name) or cur.id not in bound:
        return None
    module, _, name = bound[cur.id].rpartition(".")
    try:
        obj = importlib.import_module(bound[cur.id])
    except ImportError:
        obj = getattr(importlib.import_module(module), name, None)
    for attr in reversed(attrs):
        obj = getattr(obj, attr, None)
        if obj is None:
            return None
        if inspect.ismodule(obj) and obj.__name__ not in _REACHABLE_MODULES:
            return obj.__name__
    return None


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
