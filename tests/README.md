# CAE Dashboard Testing

Phase 1 of the testing roadmap: Backend Core Tests.

## Quick Start

### Install test dependencies

```bash
pip install -r requirements.txt
```

### Run all tests

```bash
pytest
```

### Run with coverage report

```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

### Run specific test file

```bash
pytest tests/services/test_helpers.py -v
pytest tests/routes/test_api_painel.py -v
pytest tests/db/test_duckdb_basic.py -v
```

### Run tests matching a pattern

```bash
pytest -k "test_yoy" -v
pytest -k "test_painel" -v
```

## Test Structure

### Phase 1.1: Data Integrity Tests (`tests/services/`)

- **test_helpers.py**: YoY calculations, trend detection, sparkline data
- **test_painel.py**: Section structure, KPI fields, source labels
- **test_painel_analysis.py**: Composite indicators, sentiment classification
- **test_painel_headline.py**: Prompt building, language routing, caching
- **test_interpret.py**: Ideology loading, prompt injection prevention

### Phase 1.2: API Route Tests (`tests/routes/`)

- **test_api_painel.py**: GET /api/painel validation
- **test_api_painel_headline.py**: Language + lens routing
- **test_api_painel_analysis.py**: Analysis responses
- **test_api_explore.py**: Time series filtering
- **test_api_error_handling.py**: 404, 500 responses

### Phase 1.3: Database Tests (`tests/db/`)

- **test_duckdb_basic.py**: Connection, read-only mode, data freshness
- **test_indicator_counts.py**: 380+ indicators loaded
- **test_period_coverage.py**: Expected periods for each source
- **test_data_freshness.py**: Latest period within 30 days

## Fixtures

Available in `conftest.py`:

- `sample_painel_data`: Minimal valid Painel response (7 sections, 36 KPIs)
- `sample_indicators`: 50 representative indicators
- `sample_lenses`: All 10 ideology lenses
- `sample_headlines`: Pre-generated headlines
- `temp_db`: Temporary directory for test databases
- `mock_env`: Environment variables for testing

## Coverage Goals

| Component | Current | Target |
|-----------|---------|--------|
| Backend routes | 0% | 90% |
| Business logic | 0% | 85% |
| Database access | 0% | 95% |
| **Overall** | **0%** | **75%** |

## Tips

- Tests are deterministic (no IA involved, no mocking of Anthropic API yet)
- Use `pytest -x` to stop on first failure
- Use `pytest -lf` to run last failed tests
- Use `pytest --pdb` to drop into debugger on failure
- Environment: Set `CAE_DB_PATH` to test against production DB
