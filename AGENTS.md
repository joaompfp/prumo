# AGENTS.md

> Para guidelines completas de arquitectura, convenções e ficheiros-chave, lê:
> **[`.github/copilot-instructions.md`](.github/copilot-instructions.md)**

## Quick Start

### Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scripts/create_seed_db.py
```

### Testes
```bash
CAE_DB_PATH=seed_data/seed.duckdb pytest tests/ -m "not integration and not slow" -v
```

### Lint
```bash
ruff check app/ collectors/
```

### App local
```bash
CAE_DB_PATH=seed_data/seed.duckdb uvicorn app.main:app --port 8080 --reload
```

## Restrições
- DuckDB **read-only** — sempre `read_only=True` (ver `app/database.py`)
- Padrão de serviços: `build_*()` aggregação, `compute_*()` cálculo, `get_*()` queries
- Erros: retornar `{"error": "no data", "id": ..., "label": ...}` — nunca raise em dados ausentes
- Testes: correr antes de abrir PRs; unit tests usam `seed_data/seed.duckdb`
- Lint: `ruff check` antes de push; CI falha em erros
