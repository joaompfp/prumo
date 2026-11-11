"""Runtime independence guarantee for verifiers (Ruling S).

`register_verifier`'s static check is lint; this is the guarantee. A fresh, isolated interpreter
(`python -I`) first installs
  - an import blocker (sys.meta_path) so no module `ingest.sources.<anything>` (the collectors'
    parsers) and nothing in `blocked_prefixes` can be imported by name, and
  - an audit hook (sys.addaudithook, the official API; nothing in the stdlib is patched) that
    records every file the process opens,
then imports the verifier module and calls an entrypoint that exercises it. The parent fails if
  - the child failed, or did not produce exactly one report line,
  - any loaded `ingest.*` module NAME is blocked or outside the shared infrastructure (the
    allowlist the static check uses, plus what those modules import inside `ingest`, e.g.
    ingest.validate via ingest.sources), or
  - any module in sys.modules, under ANY name, has a FILE ORIGIN inside the collectors'
    directory `ingest/sources/` (other than its `__init__.py`) or inside a blocked prefix's
    location, or any such file (source or its __pycache__ bytecode) was OPENED at all. This
    catches a parser loaded from its path under another name (spec_from_file_location +
    exec_module, which never enters sys.modules).

Still undetectable: a verifier that embeds a copy of the parser's logic (e.g. code written from
reading the parser's source while developing). Reviewers of adapter tasks must confirm the
verifier reads the independent channel (another endpoint/format/file), not the collector's.

EVERY ADAPTER TASK MUST CALL `assert_verifier_independent` IN ITS TESTS, with an entrypoint that
builds the verifier with a FakeHttp of recorded fixtures and runs `check()` on blinded items.
The entrypoint's module must itself import nothing from the collector side.
"""
import json
import secrets
import subprocess
import sys
from pathlib import Path

from ingest.verifiers import (_INGEST_ROOT, SHARED_ALLOWED, _closure, _ingest_imports,
                              _module_file, _parse)

_CHILD = r"""
import json, os, sys
args = json.loads(sys.argv[1])
exact, prefixes = set(args["blocked"]), tuple(args["prefixes"])
_opened = set()

def _audit(event, a):
    if event == "open" and a and isinstance(a[0], (str, bytes)):
        _opened.add(os.path.realpath(os.fsdecode(a[0])))

sys.addaudithook(_audit)

class _Blocker:
    @staticmethod
    def find_spec(name, path=None, target=None):
        if (name.startswith("ingest.sources.") or name in exact
                or any(name == p or name.startswith(p + ".") for p in prefixes)):
            raise ImportError(f"blocked by independence guard: {name}")
        return None

sys.meta_path.insert(0, _Blocker)
sys.path[:0] = args["path"]
import importlib, importlib.machinery

def _locate(dotted):
    # where `dotted` lives on disk, found with PathFinder directly (bypasses meta_path, executes
    # nothing): ["tree", dir] for a package, ["file", path] for a module, None if not on disk
    spec, path = None, sys.path
    for i, part in enumerate(dotted.split(".")):
        spec = importlib.machinery.PathFinder.find_spec(".".join(dotted.split(".")[:i + 1]), path)
        if spec is None:
            return None
        path = spec.submodule_search_locations
    if spec.submodule_search_locations:
        return ["tree", os.path.realpath(list(spec.submodule_search_locations)[0])]
    return ["file", os.path.realpath(spec.origin)] if spec.origin else None

sources, protected = _locate("ingest.sources"), [_locate(p) for p in prefixes]
module = importlib.import_module(args["module"])
target, _, func = args["entrypoint"].rpartition(":")
getattr(importlib.import_module(target) if target else module, func)()

def _origin(m):
    f = getattr(m, "__file__", None) or getattr(getattr(m, "__spec__", None), "origin", None)
    return os.path.realpath(f) if isinstance(f, str) and os.path.exists(f) else None

report = {"modules": {n: _origin(m) for n, m in list(sys.modules.items())},
          "opened": sorted(_opened), "sources": sources, "protected": protected}
print(args["marker"] + json.dumps(report))
"""


def assert_verifier_independent(verifier_module: str, entrypoint: str, *, source_name: str,
                                blocked_prefixes: tuple[str, ...] = (),
                                extra_sys_path: tuple[str, ...] = (),
                                timeout: float = 60.0) -> None:
    """Run `entrypoint` against `verifier_module` in a subprocess with the collector blocked.

    entrypoint: a zero-argument callable, either a name in `verifier_module` or "module:func".
    extra_sys_path: prepended to the child's sys.path before the repo root (tests use it for
        temporary modules and scratch package layouts).
    Raises AssertionError naming the problem: the child failed (its stderr tail is included),
    a blocked or non-shared `ingest.*` module was loaded, or collector/blocked code was loaded
    or opened under any name (the message names the module and the file).
    """
    repo_root = _INGEST_ROOT.parent
    marker = f"@@INGEST_REPORT_{secrets.token_hex(8)}@@"
    args = {"module": verifier_module, "entrypoint": entrypoint, "marker": marker,
            "blocked": [f"ingest.sources.{source_name}"], "prefixes": list(blocked_prefixes),
            "path": [*map(str, extra_sys_path), str(repo_root)]}
    try:
        proc = subprocess.run([sys.executable, "-I", "-c", _CHILD, json.dumps(args)],
                              cwd=repo_root, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise AssertionError(f"verifier {verifier_module} timed out after {timeout}s") from e
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise AssertionError(f"verifier {verifier_module} failed under the independence guard "
                             f"(exit {proc.returncode}):\n{tail}")
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith(marker)]
    if len(lines) != 1:
        raise AssertionError(f"verifier {verifier_module}: expected one report from the child, "
                             f"got {len(lines)}")
    report = json.loads(lines[0][len(marker):])
    loaded = {m for m in report["modules"] if m == "ingest" or m.startswith("ingest.")}
    blocked = sorted(m for m in loaded if m.startswith("ingest.sources.") or any(
        m == p or m.startswith(p + ".") for p in blocked_prefixes))
    if blocked:
        raise AssertionError(f"verifier {verifier_module} loaded blocked modules: {blocked}")
    extra = sorted(loaded - _shared_runtime_modules())
    if extra:
        raise AssertionError(f"verifier {verifier_module} loaded non-shared ingest modules: "
                             f"{extra}")
    sources_dir = Path(report["sources"][1]) if report["sources"] else None
    protected = [p for p in report["protected"] if p]

    def bad(path: str) -> bool:
        return _in_collectors(Path(path), sources_dir) or _in_protected(Path(path), protected)

    by_origin = sorted(f"{name} from {origin}" for name, origin in report["modules"].items()
                       if origin and bad(origin))
    if by_origin:
        raise AssertionError(f"verifier {verifier_module} loaded collector/blocked code under "
                             f"another name: {by_origin}")
    opened = [p for p in report["opened"] if bad(p)]
    if opened:
        raise AssertionError(f"verifier {verifier_module} opened collector/blocked files: "
                             f"{opened}")


def _in_collectors(p: Path, sources_dir: Path | None) -> bool:
    """Inside ingest/sources/, except the shared package __init__.py and its bytecode."""
    if sources_dir is None or not p.is_relative_to(sources_dir):
        return False
    return not (p.parent in (sources_dir, sources_dir / "__pycache__")
                and p.name.split(".")[0] == "__init__")


def _in_protected(p: Path, protected: list[list[str]]) -> bool:
    """A blocked prefix's file (or its bytecode) or anything in its package directory."""
    for kind, where in protected:
        w = Path(where)
        if kind == "tree" and p.is_relative_to(w):
            return True
        if kind == "file" and (p == w or (p.parent == w.parent / "__pycache__"
                                          and p.name.startswith(w.stem + "."))):
            return True
    return False


def _shared_runtime_modules() -> set[str]:
    """SHARED_ALLOWED plus the `ingest.*` modules they import themselves (read from files),
    minus any collector module; and this module, in case an entrypoint imports it."""
    reach: set[str] = set(SHARED_ALLOWED)
    for m in SHARED_ALLOWED:
        reach |= _closure_through(m)
    return {m for m in reach if not m.startswith("ingest.sources.")} | {__name__}


def _closure_through(module: str) -> set[str]:
    # _closure stops at SHARED_ALLOWED; start from each allowed module's own imports instead.
    f = _module_file(module)
    if f is None:
        return set()
    package = module if f.name == "__init__.py" else module.rpartition(".")[0]
    return _closure(_ingest_imports(_parse(f), package))
