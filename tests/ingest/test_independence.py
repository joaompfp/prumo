"""Runtime independence guard: real subprocesses over a scratch copy of the ingest package that
has a real collector parser at ingest/sources/acme.py."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import ingest
from ingest.verifiers.independence import assert_verifier_independent

CLEAN = '''
from ingest.verifiers import ItemResult


class V:
    source_name = "acme"

    def check(self, items, http):
        return [ItemResult(i.series_id, i.period, "1.5", "http://acme/table") for i in items]
'''

ENTRY = '''
from {verifier} import V
from ingest.models import SeriesSpec, SourceSpec
from ingest.verifiers import BlindItem


def run():
    src = SourceSpec(name="acme", licence="l", licence_url="http://l", attribution="a",
                     redistribution_ok=True)
    spec = SeriesSpec(id="s1", source=src, indicator_key="k", role="primary", theme="economy",
                      geography="PT", frequency="A", unit="EUR")
    [r] = V().check([BlindItem("s1", "2024", spec)], None)
    assert r.observed_text == "1.5"
'''


@pytest.fixture
def layout(tmp_path):
    """tmp/repo/ingest = copy of the real package + a parser; tmp/mods = verifier modules."""
    repo, mods = tmp_path / "repo", tmp_path / "mods"
    shutil.copytree(Path(ingest.__file__).parent, repo / "ingest",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (repo / "ingest" / "sources" / "acme.py").write_text(
        "from ingest.sources import RawResponse\n\n\ndef parse_rows(x):\n    return x\n")
    mods.mkdir()

    def write(name: str, text: str) -> None:
        (mods / f"{name}.py").write_text(text)

    def check(verifier: str, entry: str = "run", **kw) -> None:
        assert_verifier_independent(verifier, entry, source_name="acme",
                                    extra_sys_path=(mods, repo), **kw)
    return write, check, repo, mods


def test_clean_verifier_passes(layout):
    write, check, _, _ = layout
    write("clean_verifier", CLEAN + "\n\ndef run():\n    assert V().check([], None) == []\n")
    write("entry_clean", ENTRY.format(verifier="clean_verifier"))
    check("clean_verifier")
    check("clean_verifier", "entry_clean:run")


def test_verifier_inside_the_ingest_package_passes(layout):
    """Real verifiers live at ingest/verifiers/<source>.py: the verifier module itself is loaded
    by definition and is not a 'non-shared ingest module'."""
    _, check, repo, mods = layout
    (repo / "ingest" / "verifiers" / "acme.py").write_text(
        CLEAN + "\n\ndef run():\n    assert V().check([], None) == []\n")
    (mods / "entry_pkg.py").write_text(ENTRY.format(verifier="ingest.verifiers.acme"))
    check("ingest.verifiers.acme")
    check("ingest.verifiers.acme", "entry_pkg:run")


def test_a_second_ingest_verifier_module_is_still_non_shared(layout):
    _, check, repo, _ = layout
    (repo / "ingest" / "verifiers" / "other.py").write_text("X = 1\n")
    (repo / "ingest" / "verifiers" / "acme.py").write_text(
        "import ingest.verifiers.other\n" + CLEAN + "\n\ndef run():\n    pass\n")
    with pytest.raises(AssertionError, match="non-shared ingest modules.*ingest.verifiers.other"):
        check("ingest.verifiers.acme")


def test_helper_importing_the_parser_fails(layout):
    """The hole the static check cannot see: a non-ingest helper imports the parser."""
    write, check, repo, mods = layout
    write("sneaky_helper", "import ingest.sources.acme\nparse = ingest.sources.acme.parse_rows\n")
    write("sneaky_verifier", "import sneaky_helper\n" + CLEAN)
    write("entry_sneaky", ENTRY.format(verifier="sneaky_verifier"))
    # control: without the guard the parser really is reachable
    unguarded = subprocess.run(
        [sys.executable, "-I", "-c", f"import sys; sys.path[:0] = [{str(mods)!r}, {str(repo)!r}]; "
         "import sneaky_verifier; print(sneaky_verifier.sneaky_helper.parse.__module__)"],
        capture_output=True, text=True)
    assert unguarded.returncode == 0 and unguarded.stdout.strip() == "ingest.sources.acme"
    with pytest.raises(AssertionError, match="blocked by independence guard: ingest.sources.acme"):
        check("sneaky_verifier", "entry_sneaky:run")


def test_non_shared_ingest_modules_fail(layout):
    write, check, _, _ = layout
    write("db_helper", "from ingest.pipeline import run_dataset\n")
    write("db_verifier", "import db_helper\n" + CLEAN + "\n\ndef run():\n    pass\n")
    with pytest.raises(AssertionError, match=r"non-shared ingest modules: \[.*'ingest.db'"):
        check("db_verifier")


def test_blocked_prefixes_are_enforced(layout):
    write, check, _, _ = layout
    write("csv_verifier", "import csv\n" + CLEAN + "\n\ndef run():\n    pass\n")
    check("csv_verifier")
    with pytest.raises(AssertionError, match="blocked by independence guard: csv"):
        check("csv_verifier", blocked_prefixes=("csv",))


def test_entrypoint_exception_is_readable(layout):
    write, check, _, _ = layout
    write("boom_verifier", CLEAN + "\n\ndef run():\n    raise RuntimeError('boom in check')\n")
    with pytest.raises(AssertionError, match=r"(?s)failed under the independence guard.*"
                                             r"RuntimeError: boom in check"):
        check("boom_verifier")


GADGET = '''
import importlib.util
import sys
from typing import get_type_hints

from ingest.verifiers import ItemResult


def _load():
    spec = importlib.util.spec_from_file_location("zz", {parser!r})
    module = importlib.util.module_from_spec(spec)
    if {register}:
        sys.modules["zz"] = module
    spec.loader.exec_module(module)  # runs the parser under a non-ingest name
    return int


def f(x: "_load()"):  # typing evaluates string annotations with eval()
    pass


class V:
    source_name = "acme"

    def check(self, items, http):
        return [ItemResult(i.series_id, i.period, "1.5", "u") for i in items]


def run():
    get_type_hints(f)
'''


@pytest.mark.parametrize("register,message", [
    (True, r"loaded collector/blocked code under another name: \['zz from .*/ingest/sources/"
           r"acme\.py'\]"),
    (False, r"opened collector/blocked files: \['.*/ingest/sources/acme\.py'"),
])
def test_parser_loaded_by_path_under_another_name_fails(layout, register, message):
    write, check, repo, _ = layout
    parser = repo / "ingest" / "sources" / "acme.py"
    parser.write_text(parser.read_text() + f"\nopen({str(repo / 'LEAK')!r}, 'w').write('ran')\n")
    write("gadget_verifier", GADGET.format(parser=str(parser), register=register))
    with pytest.raises(AssertionError, match=message):
        check("gadget_verifier")
    assert (repo / "LEAK").read_text() == "ran"  # the gadget really executed the parser


def test_clean_verifier_importing_sources_package_passes(layout):
    """ingest/sources/__init__.py is shared infrastructure: importing Source is fine."""
    write, check, _, _ = layout
    write("pkg_verifier", "from ingest.sources import Source, RawResponse\n" + CLEAN
          + "\n\ndef run():\n    assert V().check([], None) == []\n")
    check("pkg_verifier")
