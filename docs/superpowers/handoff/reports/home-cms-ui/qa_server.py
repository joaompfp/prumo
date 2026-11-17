"""Local-only mounted acceptance server, never connected to the production database."""
import sys
from pathlib import Path

ROOT = Path('/home/joao/projects/prumo-pipeline')
sys.path.insert(0, str(ROOT))
from app.main import create_app as public_app
from backoffice.app import create_app as admin_app

DB = Path('/home/joao/.hermes/cache/scratch/prumo-home-qa/acceptance3.sqlite3')
public = public_app(str(DB))
admin = admin_app(DB, ROOT / 'registry/core.yaml', editorial_db_path=DB)


async def app(scope, receive, send):
    if scope['type'] != 'http':
        return
    path = scope['path']
    if path == '/dados/admin' or path.startswith('/dados/admin/'):
        prefix, target = '/dados/admin', admin
    elif path == '/dados' or path.startswith('/dados/'):
        prefix, target = '/dados', public
    else:
        prefix, target = '', public
    scope = dict(scope)
    scope['path'] = path[len(prefix):] or '/'
    scope['raw_path'] = scope['path'].encode()
    scope['headers'] = [(k, v) for k, v in scope['headers'] if k.lower() != b'x-forwarded-prefix']
    if prefix:
        scope['headers'].append((b'x-forwarded-prefix', prefix.encode()))
    await target(scope, receive, send)
