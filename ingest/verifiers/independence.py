"""Runtime independence guarantee for verifiers (Ruling S).

`register_verifier`'s static check is a lint-level guard; this is the guarantee. A fresh,
isolated interpreter (`python -I`) installs an import blocker before anything else, so no module
`ingest.sources.<anything>` (the collectors' parsers) and nothing in `blocked_prefixes` can be
imported; it then imports the verifier module and calls an entrypoint that exercises it. The parent
fails if the child failed, or if any loaded `ingest.*` module is outside the shared
infrastructure (the same allowlist the static check uses, plus what those modules import inside
`ingest`, e.g. ingest.validate via ingest.sources).

EVERY ADAPTER TASK MUST CALL `assert_verifier_independent` IN ITS TESTS, with an entrypoint that
builds the verifier with a FakeHttp of recorded fixtures and runs `check()` on blinded items.
The entrypoint's module must itself import nothing from the collector side.
"""
import json
import subprocess
import sys

from ingest.verifiers import (_INGEST_ROOT, SHARED_ALLOWED, _closure, _ingest_imports,
                              _module_file, _parse)

_MARKER = "@@INGEST_MODULES@@"
_CHILD = r"""
import json, sys
args = json.loads(sys.argv[1])
exact, prefixes = set(args["blocked"]), tuple(args["prefixes"])

class _Blocker:
    @staticmethod
    def find_spec(name, path=None, target=None):
        if (name.startswith("ingest.sources.") or name in exact
                or any(name == p or name.startswith(p + ".") for p in prefixes)):
            raise ImportError(f"blocked by independence guard: {name}")
        return None

sys.meta_path.insert(0, _Blocker)
sys.path[:0] = args["path"]
import importlib
module = importlib.import_module(args["module"])
target, _, func = args["entrypoint"].rpartition(":")
getattr(importlib.import_module(target) if target else module, func)()
print(args["marker"] + json.dumps(sorted(m for m in sys.modules
                                         if m == "ingest" or m.startswith("ingest."))))
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
    a blocked module was loaded, or non-shared `ingest.*` modules were loaded.
    """
    repo_root = _INGEST_ROOT.parent
    args = {"module": verifier_module, "entrypoint": entrypoint, "marker": _MARKER,
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
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith(_MARKER)]
    if not lines:
        raise AssertionError(f"verifier {verifier_module}: no module report from the child")
    loaded = set(json.loads(lines[-1][len(_MARKER):]))
    blocked = sorted(m for m in loaded if m.startswith("ingest.sources.") or any(
        m == p or m.startswith(p + ".") for p in blocked_prefixes))
    if blocked:
        raise AssertionError(f"verifier {verifier_module} loaded blocked modules: {blocked}")
    extra = sorted(loaded - _shared_runtime_modules())
    if extra:
        raise AssertionError(f"verifier {verifier_module} loaded non-shared ingest modules: "
                             f"{extra}")


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
