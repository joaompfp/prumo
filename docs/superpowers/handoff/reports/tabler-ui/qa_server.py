"""Local acceptance host. Refuses database paths outside Hermes scratch."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from app.main import create_app as public_app
from backoffice.app import create_app as admin_app

DB = Path(os.environ["PRUMO_QA_DB"]).resolve(strict=True)
SCRATCH = Path("/home/joao/.hermes/cache/scratch").resolve()
if not DB.is_relative_to(SCRATCH):
    raise ValueError("Acceptance writes may only target an isolated scratch database")
public = public_app(str(DB))
admin = admin_app(DB, ROOT / "registry/core.yaml", editorial_db_path=DB)


async def app(scope, receive, send):
    if scope["type"] != "http":
        return
    path = scope["path"]
    if path == "/dados/admin" or path.startswith("/dados/admin/"):
        prefix, target = "/dados/admin", admin
    elif path == "/dados" or path.startswith("/dados/"):
        prefix, target = "/dados", public
    else:
        prefix, target = "", public
    scope = dict(scope)
    scope["path"] = path[len(prefix):] or "/"
    scope["raw_path"] = scope["path"].encode()
    scope["headers"] = [(k, v) for k, v in scope["headers"] if k.lower() != b"x-forwarded-prefix"]
    if prefix:
        scope["headers"].append((b"x-forwarded-prefix", prefix.encode()))
    await target(scope, receive, send)
