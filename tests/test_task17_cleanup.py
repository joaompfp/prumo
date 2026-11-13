"""Task 17 cleanup boundaries: permanent regression guards.

These tests pin the contract decided in the Task 17 cleanup:

- superseded legacy collectors/scripts are deleted and stay deleted;
- explicitly retained historical artifacts stay byte-present;
- the dadosgov/habitacao bare-base-import consumers of collectors/base.py stay;
- active runtime code (app/, ingest/) never imports retired collector modules or
  the legacy DuckDB/pyarrow store libraries;
- CI installs runtime requirements only, never builds a legacy seed DB, exercises
  app+ingest coverage, lints supported code only, and never re-enables live tests;
- the old maintenance-UI fixtures stay removed from tests/conftest.py.

They are filesystem/AST/YAML inspections only: no network, no legacy database code.
"""
import ast
import configparser
import shlex
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent

# -- Deletion set (Task 17 consent, exact) -------------------------------------

RETIRED_FILES = [
    "collectors/eurostat.py",
    "collectors/ine.py",
    "collectors/bportugal.py",
    "collectors/ren.py",
    "collectors/worldbank.py",
    "collectors/fred.py",
    "collectors/oecd.py",
    "collectors/eredes.py",
    "scripts/collect_scheduled.py",
    "scripts/audit_nightly.py",
    "scripts/backfill_eu27.py",
    "scripts/backfill_full.py",
    "scripts/backfill_missing.py",
    "scripts/collectors/cae-collect",
    "scripts/collectors/cae-v4-backfill.py",
    "scripts/collectors/collect_electricity_prices.py",
    "scripts/collectors/collect_gdp_per_capita_ppp.py",
    "scripts/collectors/collect_hourly_earnings.py",
    "scripts/collectors/collect_price_level_index.py",
    "scripts/collectors/collect_stale_data.py",
    "scripts/collectors/collect_worldbank_global.py",
    "scripts/maintenance/merge_staging.py",
    "scripts/maintenance/normalize_db.py",
]

PRESERVED_FILES = [
    "collectors/base.py",
    "collectors/dadosgov.py",
    "collectors/dgeg_fuel_api.py",
    "collectors/habitacao.py",
    "collectors/collect_new_indicators.py",
    "scripts/create_seed_db.py",
    "scripts/ingest.py",
    "Dockerfile",
    "entrypoint.sh",
]

RETIRED_MODULE_ROOTS = {
    "eurostat",
    "ine",
    "bportugal",
    "ren",
    "worldbank",
    "fred",
    "oecd",
    "eredes",
    "collectors",
}

LEGACY_DB_LIBS = {"duckdb", "pyarrow"}

ACTIVE_DIRS = ["app", "ingest"]

OLD_UI_FIXTURES = {
    "sample_painel_data",
    "sample_indicators",
    "sample_lenses",
    "sample_headlines",
    "temp_db",
    "mock_env",
}


def _imports_in(path: Path):
    """Yield dotted import roots used by a Python file (AST only)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split(".")[0]


def _active_py_files():
    for d in ACTIVE_DIRS:
        yield from sorted((REPO / d).rglob("*.py"))


# -- Removal / preservation ----------------------------------------------------


@pytest.mark.parametrize("rel", RETIRED_FILES)
def test_retired_legacy_file_removed(rel):
    assert not (REPO / rel).exists(), f"retired legacy file still present: {rel}"


def test_retired_legacy_dirs_gone():
    assert not (REPO / "scripts" / "collectors").exists()
    assert not (REPO / "scripts" / "maintenance").exists()


@pytest.mark.parametrize("rel", PRESERVED_FILES)
def test_preserved_file_still_present(rel):
    assert (REPO / rel).is_file(), f"protected file missing: {rel}"


@pytest.mark.parametrize("consumer", ["collectors/dadosgov.py", "collectors/habitacao.py"])
def test_bare_base_consumers_preserved(consumer):
    """dadosgov/habitacao import collectors/base.py via a bare `from base import ...`
    after sys.path manipulation; prefix-only `from collectors` searches miss them."""
    text = (REPO / consumer).read_text(encoding="utf-8")
    assert "from base import" in text, f"{consumer} no longer consumes base.py bare"
    assert "standardize_rows" in text and "write_parquet" in text


def test_collect_new_indicators_retained_but_not_runnable_entrypoint():
    """Retained historical artifact still references the retired clients it needs."""
    text = (REPO / "collectors" / "collect_new_indicators.py").read_text(encoding="utf-8")
    assert "BPortugalClient" in text  # historical code, NOT an operational entrypoint
    assert (REPO / "collectors" / "README.md").is_file(), "collectors/README.md missing"


# -- Active runtime import hygiene ---------------------------------------------


def test_active_code_never_imports_retired_collectors():
    offenders = []
    for path in _active_py_files():
        for root in _imports_in(path):
            if root in RETIRED_MODULE_ROOTS:
                offenders.append(f"{path.relative_to(REPO)} imports {root!r}")
    assert not offenders, "\n".join(offenders)


def test_active_runtime_has_no_legacy_db_libs():
    """duckdb/pyarrow belong to the legacy seed/inspection scripts only."""
    offenders = []
    for path in _active_py_files():
        for root in _imports_in(path):
            if root in LEGACY_DB_LIBS:
                offenders.append(f"{path.relative_to(REPO)} imports {root!r}")
    assert not offenders, "\n".join(offenders)


# -- tests/conftest.py old-UI fixtures ------------------------------------------


def test_conftest_old_ui_fixtures_removed():
    tree = ast.parse(
        (REPO / "tests" / "conftest.py").read_text(encoding="utf-8"),
        filename="tests/conftest.py",
    )
    defined = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "fixture"
                    or isinstance(target, ast.Name)
                    and target.id == "fixture"
                ):
                    defined.add(node.name)
    still = defined & OLD_UI_FIXTURES
    assert not still, f"old-UI fixtures still defined in conftest: {sorted(still)}"


def test_conftest_keeps_import_bootstrap():
    text = (REPO / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "sys.path" in text, "conftest import-path bootstrap must be preserved"


# -- pytest / coverage configuration --------------------------------------------


def test_pytest_ini_default_excludes_live():
    cfg = configparser.ConfigParser()
    cfg.read(REPO / "pytest.ini")
    addopts = cfg["pytest"].get("addopts", "")
    assert 'not live' in addopts, "default pytest selection must exclude live tests"


def test_coverage_config_consumed():
    """pytest.ini [coverage:*] sections are not consumed by coverage.py; a real
    config file must cover both app and ingest with branch coverage."""
    cov = configparser.ConfigParser()
    cov.read(REPO / ".coveragerc")
    source = cov["run"].get("source", "")
    assert "app" in source and "ingest" in source
    assert cov["run"].get("branch", "").strip().lower() == "true"


# -- CI workflow contract --------------------------------------------------------


def _ci():
    # yaml 1.1 parses the literal key `on` as True; address jobs generically.
    doc = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text())
    return doc["jobs"]


def _ci_steps():
    for job in _ci().values():
        for step in job.get("steps", []):
            yield step


def _ci_run_strings():
    return [step.get("run", "") for step in _ci_steps()]


def _ci_env_keys():
    keys = set()
    for job in _ci().values():
        keys |= set((job.get("env") or {}).keys())
        for step in job.get("steps", []):
            keys |= set((step.get("env") or {}).keys())
    return keys


def test_ci_installs_runtime_requirements_only():
    installs = [r for r in _ci_run_strings() if "pip install" in r]
    assert any("requirements.txt" in r for r in installs), "CI must install requirements.txt"
    assert not any(
        "requirements-legacy" in r for r in installs
    ), "CI must not install legacy DuckDB/pyarrow requirements"


def test_ci_has_no_legacy_seed_or_db_env():
    blob = "\n".join(_ci_run_strings())
    assert "create_seed_db" not in blob, "CI must not build the legacy seed DB"
    assert "CAE_DB_PATH" not in _ci_env_keys(), "CI must not set CAE_DB_PATH"


def test_ci_exercises_app_and_ingest_coverage():
    pytest_runs = [r for r in _ci_run_strings() if "pytest" in r]
    assert pytest_runs, "CI must run pytest"
    cmd = max(pytest_runs, key=len)
    assert "--cov=app" in cmd and "--cov=ingest" in cmd, "coverage must target app+ingest"


def test_ci_never_reenables_live_tests():
    for cmd in _ci_run_strings():
        tokens = shlex.split(cmd)
        if "pytest" not in tokens:
            continue
        marker_sel = []
        for i, tok in enumerate(tokens):
            if tok == "-m" and i + 1 < len(tokens):
                marker_sel.append(tokens[i + 1])
            elif tok.startswith("-m="):
                marker_sel.append(tok.split("=", 1)[1])
        for expr in marker_sel:
            assert "not live" in expr, (
                "a custom -m selection overrides the default 'not live' guard: " + cmd
            )
    assert not any(
        "not integration and not slow" in r for r in _ci_run_strings()
    ), "the old CI expression re-enabled live tests"


def test_ci_lints_supported_code_only():
    lint_cmds = [r for r in _ci_run_strings() if "ruff" in r]
    assert lint_cmds, "CI must lint"
    blob = "\n".join(lint_cmds)
    assert "app" in blob and "ingest" in blob
    assert "collectors" not in blob, "retained historical collectors are out of the lint gate"
