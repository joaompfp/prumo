"""Pytest configuration for the Prumo test suite.

Only the import-path bootstrap lives here; the old maintenance-UI fixtures were
removed in the Task 17 cleanup (no surviving test consumed them). Pipeline-scoped
fixtures live in tests/ingest/conftest.py.
"""
import sys
from pathlib import Path

# Add repo root to path so `app` and `ingest` import directly under pytest.
sys.path.insert(0, str(Path(__file__).parent.parent))
