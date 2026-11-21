"""Serve the candidate public/Admin shells against an isolated scratch database only."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from app.main import create_app as public_app  # noqa: E402
from backoffice.app import create_app as admin_app  # noqa: E402

DB = Path(os.environ["PRUMO_QA_DB"]).resolve(strict=True)
if not DB.is_relative_to(Path("/home/joao/.hermes/cache/scratch")):
    raise ValueError("Isolated scratch database required")
public = public_app(str(DB))
admin = admin_app(DB, ROOT / "registry/core.yaml", editorial_db_path=DB)


async def app(scope, receive, send):
    if scope["type"] != "http":
        await public(scope, receive, send)
        return
    scope = dict(scope)
    path = scope["path"]
    prefix = next((candidate for candidate in ("/dados/admin", "/dados")
                   if path == candidate or path.startswith(candidate + "/")), "")
    scope["path"] = path[len(prefix):] or "/"
    scope["raw_path"] = scope["path"].encode()
    scope["headers"] = [(key, value) for key, value in scope["headers"]
                        if key.lower() != b"x-forwarded-prefix"]
    if prefix:
        scope["headers"].append((b"x-forwarded-prefix", prefix.encode()))
    await (admin if prefix == "/dados/admin" else public)(scope, receive, send)
