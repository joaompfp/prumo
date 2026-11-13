"""Task 19A: offline registry documentation, including blocked and empty sources."""
import html
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from ingest.models import SourceSpec
from ingest.registry import load_registry

ROOT = Path(__file__).parents[2]
CORE = ROOT / "registry/core.yaml"
GENERATED = ROOT / "docs/data/sources.md"
SOURCE = {"licence": "Test grant", "licence_url": "https://example.invalid/terms",
          "attribution": "Test publisher", "redistribution_ok": True}


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("documentation must not use the network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def _row(sid, key, source="custom", *, active=True, role="primary"):
    return {"id": sid, "indicator_key": key, "source": source, "role": role,
            "active": active, "theme": "economy", "geography": "PT", "frequency": "M",
            "unit": "EUR", "native_code": "EXACT:code=PT"}


def _registry(tmp_path, sources=None, series=None):
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump({"sources": sources if sources is not None else {
        "custom": SOURCE}, "series": series if series is not None else [
            _row("custom.primary.PT", "custom.PT.M")]}), encoding="utf-8")
    return path


def _section(text, name):
    return next(part for part in text.split("\n## ")[1:]
                if html.unescape(part.splitlines()[0]) == name)


def _table_rows(section):
    return [[html.unescape(cell.strip()) for cell in line.strip("|").split("|")]
            for line in section.splitlines() if line.startswith("| ")][1:]


def test_sources_md_lists_every_source_with_licence():
    from ingest.docgen import generate_sources

    text = generate_sources(CORE)
    doc = yaml.safe_load(CORE.read_text())
    assert len(text.split("\n## ")) - 1 == len(doc["sources"])
    for name, source in doc["sources"].items():
        section = html.unescape(_section(text, name))
        assert f"Licence: {source['licence']}\n" in section
        assert f"Licence URL: {source['licence_url']}\n" in section
        assert f"Attribution: {source['attribution']}\n" in section
        assert f"redistribution_ok={str(source['redistribution_ok']).lower()}" in section
        assert f"verifiable={str(source.get('verifiable', True)).lower()}" in section


def test_sources_md_contains_every_exact_series_identity_and_state():
    from ingest.docgen import generate_sources

    text = generate_sources(CORE)
    doc = yaml.safe_load(CORE.read_text())
    specs = sorted(load_registry(CORE), key=lambda s: s.id)
    for name in doc["sources"]:
        actual = _table_rows(_section(text, name))
        expected = [[s.id, s.indicator_key, s.role, "active" if s.active else "inactive",
                     s.native_code or "Not specified"]
                    for s in specs if s.source.name == name]
        assert actual == expected


def test_generated_sources_is_current_and_repeatable():
    from ingest.docgen import generate_sources

    first = generate_sources(CORE)
    assert first == generate_sources(CORE)
    assert GENERATED.read_text(encoding="utf-8") == first
    assert first.endswith("\n") and not first.endswith("\n\n")
    assert "python -m ingest docs > docs/data/sources.md" in first
    assert "--registry PATH docs" in first
    assert "not a production status report" in first


def test_renderer_is_pure_and_independent_of_registry_order(tmp_path):
    from ingest.docgen import render_sources

    sources = [SourceSpec(name="zero", **SOURCE), SourceSpec(name="custom", **SOURCE)]
    path = _registry(tmp_path, series=[_row("z", "z"), _row("a", "a", active=False)])
    specs = load_registry(path)
    before = ([s.model_dump() for s in sources], [s.model_dump() for s in specs])
    rendered = render_sources(sources, specs)
    assert rendered == render_sources(list(reversed(sources)), list(reversed(specs)))
    assert before == ([s.model_dump() for s in sources], [s.model_dump() for s in specs])


def test_zero_series_blocked_and_inactive_definitions_are_retained(tmp_path):
    from ingest.docgen import generate_sources

    sources = {"zero": {**SOURCE, "redistribution_ok": False, "verifiable": False},
               "custom": SOURCE}
    path = _registry(tmp_path, sources, [_row("inactive.id", "inactive.key", active=False)])
    text = generate_sources(path)
    zero = _section(text, "zero")
    assert "redistribution_ok=false" in zero and "verifiable=false" in zero
    assert "No series defined." in zero
    assert "Undocumented" in zero
    assert _table_rows(_section(text, "custom")) == [
        ["inactive.id", "inactive.key", "primary", "inactive", "EXACT:code=PT"]]
    # Public ingestion loader stays a list of series, not a new source/series wrapper.
    assert [s.id for s in load_registry(path)] == ["inactive.id"]


def test_empty_registry_has_no_invented_sources(tmp_path):
    from ingest.docgen import generate_sources

    text = generate_sources(_registry(tmp_path, {}, []))
    assert "\n## " not in text
    assert "No source definitions." in text


def test_cross_checks_do_not_displace_primary_or_inactive_entries(tmp_path):
    from ingest.docgen import generate_sources

    path = _registry(tmp_path, series=[_row("p", "key"),
                                     _row("c", "key", role="cross_check", active=False)])
    rows = _table_rows(_section(generate_sources(path), "custom"))
    assert rows == [["c", "key", "cross_check", "inactive", "EXACT:code=PT"],
                    ["p", "key", "primary", "active", "EXACT:code=PT"]]


@pytest.mark.parametrize(("name", "markers"), [
    ("bportugal", ("/api/observations/", "/api/series/", "JSON-stat")),
    ("eredes", ("/exports/csv", "timezone=UTC", "metadata")),
    ("eurostat", ("/sdmx/2.1/data/", "TSV", "JSON-stat")),
    ("fred", ("https://fred.stlouisfed.org/data/", "HTML", "JSON")),
    ("ine", ("bddXplorer04.jsp", "Referer", "JSON")),
    ("oecd", ("csvfilewithlabels", "AllDimensions", "SDMX-JSON")),
    ("ren", ("https://datahub.ren.pt/service/exports/csv", "1550", "2649")),
    ("worldbank", ("downloadformat=csv", "ZIP", "en", "es", "SL.UEM.TOTL.ZS")),
])
def test_reviewed_channel_descriptions_are_explicit(name, markers):
    from ingest.docgen import generate_sources

    section = html.unescape(_section(generate_sources(CORE), name))
    for marker in markers:
        assert marker in section
    assert f"ingest/verifiers/{name}.py" in section


def test_dgeg_is_scoped_blocked_not_a_fictional_verifier():
    from ingest.docgen import generate_sources

    section = html.unescape(_section(generate_sources(CORE), "dgeg"))
    assert "Undocumented for current core definitions" in section
    assert "partial" in section.lower() and "PDF" in section
    assert "registry/unmapped-dgeg.md" in section
    assert "ingest/verifiers/dgeg.py" not in section
    assert all(row[3] == "inactive" for row in _table_rows(section))


def test_metadata_is_escaped_without_losing_readable_values(tmp_path):
    from ingest.docgen import generate_sources

    nasty = '<script>alert("x")</script> | [link](javascript:bad) `x` *bold* \\ tail\n## fake'
    source = {**SOURCE, "licence": nasty, "attribution": nasty,
              "licence_url": "javascript:<bad>|`[x]`"}
    path = _registry(tmp_path, {"custom": source}, [_row(nasty, nasty)])
    text = generate_sources(path)
    section = _section(text, "custom")
    assert '<script>' not in text and "javascript:<bad>" not in text
    assert "[link](javascript:bad)" not in text and "`x`" not in text
    assert "*bold*" not in text and "\n## fake" not in text
    assert html.unescape(section).count(nasty.replace("\n", "<br>")) == 4
    assert all(len(row) == 5 for row in _table_rows(section))


def test_docs_cli_is_early_stdout_only_and_has_no_operational_side_effects(
        tmp_path, monkeypatch, capsys):
    import ingest.cli as cli
    from ingest.docgen import generate_sources

    path = _registry(tmp_path)
    db, raw = tmp_path / "must-not-exist.sqlite3", tmp_path / "must-not-exist-raw"

    def forbidden(*args, **kwargs):
        raise AssertionError("docs must return before operational setup")

    for name in ("_resolve_paths", "load_registry", "open_db", "RawStore", "sync_registry",
                 "run_all", "_http_for"):
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(cli.operations, "ensure_verifier", forbidden)
    before = set(tmp_path.iterdir())
    assert cli.main(["--registry", str(path), "--db", str(db), "--raw-dir", str(raw),
                     "docs"], http_for=forbidden) == 0
    out = capsys.readouterr()
    assert out.out == generate_sources(path) and out.err == ""
    assert set(tmp_path.iterdir()) == before
    assert not db.exists() and not raw.exists()


def test_docs_cli_default_registry_matches_generated(capsys):
    from ingest.cli import main

    assert main(["docs"]) == 0
    assert capsys.readouterr().out == GENERATED.read_text(encoding="utf-8")


def test_docs_cli_help_documents_stdout(capsys):
    from ingest.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["docs", "--help"])
    assert exc.value.code == 0
    assert "stdout" in capsys.readouterr().out


def test_docgen_import_and_render_do_not_import_source_or_verifier_implementations(tmp_path):
    path = _registry(tmp_path)
    script = '''
import importlib.abc
import json
import socket
import sqlite3
import sys

def forbidden(*args, **kwargs):
    raise AssertionError("no network or DB allowed")
socket.socket.connect = forbidden
socket.create_connection = forbidden
sqlite3.connect = forbidden
class BlockImplementations(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("ingest.sources", "ingest.verifiers")):
            raise AssertionError("documentation imported implementation: " + fullname)
sys.meta_path.insert(0, BlockImplementations())
from ingest.docgen import generate_sources
text = generate_sources(sys.argv[1])
assert "custom" in text
assert not any(n.startswith(("ingest.sources", "ingest.verifiers")) for n in sys.modules)
print(json.dumps({"offline": True}))
'''
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-c", script, str(path)], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"offline": True}


@pytest.mark.parametrize("case", ["duplicate", "unknown", "missing-primary", "empty-licence"])
def test_documentation_keeps_registry_validation(tmp_path, case):
    from ingest.docgen import generate_sources

    sources, series = {"custom": SOURCE}, [_row("a", "a")]
    if case == "duplicate":
        series.append(_row("a", "b"))
    elif case == "unknown":
        series[0]["source"] = "missing"
    elif case == "missing-primary":
        series[0]["role"] = "cross_check"
    else:
        sources["zero"] = {**SOURCE, "licence": " "}
    with pytest.raises(ValueError):
        generate_sources(_registry(tmp_path, sources, series))
