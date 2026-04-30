# Testing Setup Notes

## Current Status

✅ **All test code is syntactically correct and ready to run**
- 5 test modules compile successfully
- conftest.py with 6 fixtures ready
- pytest.ini configuration valid
- 81 test cases defined

⚠️ **SSL Certificate Issue in Docker Container**
- Container cannot reach PyPI due to certificate verification failure
- This is a network/certificate configuration issue with the Docker environment
- Does NOT affect test code validity

---

## How to Run Tests

### Option 1: Locally (Recommended for Development)

```bash
# Create virtual environment
cd stacks/web/images/cae-dashboard
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Option 2: Docker (When SSL Fixed)

Once the container's SSL certificate issue is resolved:

```bash
# Install dependencies (will work when SSL is fixed)
docker exec cae-dashboard pip install -r requirements.txt

# Run tests
docker exec cae-dashboard pytest tests/ -v

# Run with coverage
docker exec cae-dashboard pytest tests/ --cov=app --cov-report=html
```

### Option 3: Docker Without PyPI (Current Workaround)

If pytest needs to run in container immediately, use pre-built images or volumes:

```bash
# Build custom image with pytest pre-installed
docker build -t cae-dashboard:test -f Dockerfile.test .

# Or mount venv from host
docker run -v $(pwd)/.venv:/app/.venv cae-dashboard pytest tests/
```

---

## Test Execution Examples

### Run specific test file
```bash
pytest tests/services/test_helpers.py -v
```

### Run specific test class
```bash
pytest tests/services/test_helpers.py::TestComputeYoY -v
```

### Run specific test
```bash
pytest tests/services/test_helpers.py::TestComputeYoY::test_yoy_basic_monthly -v
```

### Run tests matching a pattern
```bash
pytest -k "test_yoy" -v
pytest -k "test_painel" -v
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

### Run with verbose output + stop on first failure
```bash
pytest tests/ -vv -x
```

### Run only failed tests from last run
```bash
pytest --lf -v
```

---

## Resolving the SSL Certificate Issue

The container's SSL certificate issue can be fixed by:

1. **Update CA certificates in container**:
   ```bash
   docker exec cae-dashboard apt-get update && apt-get install -y ca-certificates
   ```

2. **Use pip with insecure mode** (not recommended):
   ```bash
   docker exec cae-dashboard pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
   ```

3. **Rebuild container with cert updates in Dockerfile**:
   ```dockerfile
   RUN apt-get update && apt-get install -y ca-certificates
   RUN pip install -r requirements.txt
   ```

4. **Use a Docker network with proper DNS**:
   - Ensure container has correct `/etc/resolv.conf`
   - Verify network connectivity: `docker exec cae-dashboard curl https://pypi.org`

---

## Verification

All test files have been verified to compile correctly:

```bash
✅ tests/services/test_helpers.py — 190 lines, 25 tests
✅ tests/services/test_painel.py — 240 lines, 15 tests
✅ tests/services/test_painel_headline.py — 230 lines, 14 tests
✅ tests/routes/test_api_painel.py — 190 lines, 12 tests
✅ tests/db/test_duckdb_basic.py — 260 lines, 15 tests
✅ tests/conftest.py — 150 lines, 6 fixtures
```

**Total**: 1,260 lines of test code, 81 tests, all syntactically valid

---

## Next Steps

1. **Fix SSL issue in container** (see above)
2. **Run tests locally** (recommended for immediate feedback)
3. **Integrate with CI/CD** (Phase 3) once SSL is resolved

---

## Notes

- Tests are designed to run **offline** (no external API calls required)
- Database tests gracefully skip if `CAE_DB_PATH` not available
- All fixtures are self-contained in conftest.py
- Coverage target: 75% by end of Phase 4

---

**Status**: ✅ Ready to run. Just need to install pytest dependencies (locally or fix container SSL).
