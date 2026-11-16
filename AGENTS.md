# AGENTS.md

> A UI antiga foi removida (tag `legacy-ui-final`); a app serve "Em manutenção" enquanto o pipeline `ingest/` é construído.
> Deploy: f0nix, aliases `dc-web-*` (ver `CLAUDE.md`).

## Quick Start

### Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Testes
```bash
pytest tests/ -v
```

### Lint
```bash
ruff check app/ collectors/
```

### App local
```bash
uvicorn app.main:app --port 8080 --reload
```

## Restrições
- Texto: nunca usar em dashes (U+2014); usar hífen (-). A regra aplica-se a código, interface, documentação e testes; preservar os originais das fontes.
- Lint: `ruff check` antes de push; CI falha em erros
- Testes: correr antes de abrir PRs
