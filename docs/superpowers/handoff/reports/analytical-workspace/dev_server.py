"""Local-only public-app wrapper for workspace acceptance at both public mount shapes.

Run against an isolated scratch SQLite backup using PRUMO_DB_PATH. This helper does not
migrate, publish CMS content, inject an identity or expose administrative routes.
"""
from fastapi import FastAPI

from app.main import create_app

public = create_app()
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/dados', public)
app.mount('/', public)
