"""Independent verifier contract (spec 6b). One verifier per source (Tasks 9-16) implements
`Verifier`; it re-reads sampled observations through a channel different from the collector's
(another endpoint or format, the publisher's web table, a downloadable file) and must not reuse the
collector's parser. `register_verifier` enforces the last part on the verifier's own module.
"""
import ast
import importlib.util
import inspect
import sys
from dataclasses import dataclass
from typing import Literal, Protocol

import ingest.sources as _sources_pkg
from ingest.http import Http
from ingest.models import SeriesSpec

_SOURCES = "ingest.sources"
_REGISTRY: dict[str, "Verifier"] = {}


@dataclass(frozen=True)
class SampleItem:
    """One sampled observation, as stored by the run under verification."""
    series_id: str
    period: str  # canonical period
    expected_text: str  # stored value_text (publisher token, in spec.decimal format)
    spec: SeriesSpec
    expected_unit: str
    expected_flag: str | None


@dataclass(frozen=True)
class ItemResult:
    """What the independent channel shows for one SampleItem.

    observed_text: the publisher's number as shown there, None = not found (a mismatch).
    evidence_url: where it was read (URL incl. query, or file URL + locator), for the audit.
    observed_decimal: decimal separator of observed_text.
    observed_unit / observed_flag: None = this channel does not expose them (not compared).
    series_id / period: SHOULD echo the item's key; when given they must equal it, so a result
        returned out of order is caught instead of being compared against the wrong item.
    """
    observed_text: str | None
    evidence_url: str
    observed_decimal: Literal[".", ","] = "."
    observed_unit: str | None = None
    observed_flag: str | None = None
    series_id: str | None = None
    period: str | None = None


class Verifier(Protocol):
    """source_name: the registry source this verifier checks.
    check: one ItemResult per item, same length and order; may raise (counted as a failure)."""
    source_name: str

    def check(self, items: list[SampleItem], http: Http) -> list[ItemResult]: ...


def register_verifier(verifier: Verifier) -> None:
    """Register the verifier of `verifier.source_name`.

    ValueError if one is already registered for that source, or if the module defining the
    verifier's class imports (anywhere in its AST, relative imports resolved) a collector module:
    any `ingest.sources.<submodule>`, or any module named like the source (a dotted-name
    component equal to source_name, outside ingest.verifiers). Allowed: the `ingest.sources`
    package itself and its non-module names (protocol types such as RawResponse), ingest.http,
    ingest.models, ingest.verifiers, the stdlib, third-party libraries.
    Limits (documented, not enforced): only the verifier's own module is inspected (no transitive
    imports) and dynamic imports (importlib.import_module) are not seen.
    """
    name = verifier.source_name
    if name in _REGISTRY:
        raise ValueError(f"a verifier for source {name!r} is already registered")
    bad = _parser_imports(type(verifier), name)
    if bad:
        raise ValueError(f"verifier for {name!r} must be independent of the collector, but its "
                         f"module imports {bad}")
    _REGISTRY[name] = verifier


def get_verifier(source_name: str) -> Verifier:
    """The registered verifier of `source_name` (KeyError if none)."""
    return _REGISTRY[source_name]


def _parser_imports(cls: type, source_name: str) -> list[str]:
    module = sys.modules.get(cls.__module__)
    path = inspect.getsourcefile(module) if module is not None else None
    if path is None:
        raise ValueError(f"cannot inspect the imports of {cls.__module__!r} (no source file)")
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    package = module.__package__ or ""
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bad += [a.name for a in node.names if _forbidden(a.name, source_name)]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                try:
                    base = importlib.util.resolve_name("." * node.level + base, package)
                except ImportError as e:
                    raise ValueError(f"cannot resolve a relative import in {path}: {e}") from e
            if _forbidden(base, source_name):
                bad.append(base)
            for a in node.names:
                full = f"{base}.{a.name}"
                if a.name == "*":
                    continue
                if base == _SOURCES:
                    if _is_source_submodule(a.name):
                        bad.append(full)
                elif _forbidden(full, source_name):
                    bad.append(full)
    return sorted(set(bad))


def _forbidden(dotted: str, source_name: str) -> bool:
    if dotted.startswith(_SOURCES + "."):
        return True
    return (source_name in dotted.split(".")
            and not dotted.startswith("ingest.verifiers"))


def _is_source_submodule(name: str) -> bool:
    """True unless `name` is a plain (non-module) attribute of the ingest.sources package."""
    obj = getattr(_sources_pkg, name, None)
    return (obj is None or inspect.ismodule(obj)
            or importlib.util.find_spec(f"{_SOURCES}.{name}") is not None)
