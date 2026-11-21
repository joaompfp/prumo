"""Host-side installation of authorized real CMS content, with exact readback and receipts.

Run on f0nix only after compatible web/Admin readers are installed. The only mutation is inside
its existing restricted backoffice writer; SQL here is read-only installation evidence.
"""
import hashlib
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DATA = Path('/home/joao/docker/stacks/web/appdata/prumo/prumo.sqlite3')
RECEIPT = Path('/home/joao/prumo-operations/cms-comparisons-release-20261121/content.json')
CMS_TABLES = {'cms_document', 'cms_revision', 'cms_event', 'sqlite_sequence'}


def snapshot():
    conn = sqlite3.connect(f'file:{DATA}?mode=ro', uri=True)
    try:
        conn.execute('BEGIN')
        tables = {}
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            digest = hashlib.sha256()
            count = 0
            for row in conn.execute(f'SELECT * FROM "{name}" ORDER BY rowid'):
                digest.update(json.dumps(row, ensure_ascii=False, default=repr).encode())
                digest.update(b'\n')
                count += 1
            tables[name] = {'rows': count, 'sha256': digest.hexdigest()}
        heads = list(conn.execute("SELECT kind,slug,version,draft_revision_id,published_revision_id FROM cms_document ORDER BY kind,slug"))
        schema = list(conn.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name'))
        return {'at': datetime.now(timezone.utc).isoformat(), 'tables': tables, 'heads': heads,
                'schema': hashlib.sha256(json.dumps(schema).encode()).hexdigest(),
                'integrity': list(conn.execute('PRAGMA quick_check')),
                'foreign_keys': list(conn.execute('PRAGMA foreign_key_check')),
                'home': list(conn.execute("SELECT * FROM cms_document WHERE kind='page' AND slug='inicio'"))}
    finally:
        conn.close()


def main():
    before = snapshot()
    code = '''import json,os
from pathlib import Path
from backoffice.cms import Cms
from backoffice.comparison_import import definitions,install
cms=Cms(Path('/data/prumo.sqlite3'),Path(os.environ['PRUMO_EDITORIAL_DB']))
result=install(cms,actor='operator:jarbas',note='Conversão dos comparativos reais para autoria CMS autorizada pelo João',publish=True)
repeated=install(cms,actor='operator:jarbas',note='Confirmar importação sem substituir conteúdo',publish=True)
heads=[]
for entry in definitions():
    doc=cms.get('chart',entry.slug)
    assert doc is not None and doc['published'] is not None,entry.slug
    heads.append({'slug':entry.slug,'title':doc['published'].title,'series':list(doc['published'].series_ids),'axes':doc['published'].axes,'category':doc['published'].comparison_group,'version':doc['meta']['version'],'revision':doc['meta']['published_revision_id'],'events':len(doc['events'])})
print(json.dumps({'import':result,'repeated':repeated,'heads':heads},ensure_ascii=False))
'''
    result = subprocess.run(['docker', 'exec', '-i', '-w', '/app', 'prumo-backoffice', 'python3', '-'],
                            input=code, text=True, capture_output=True, timeout=180)
    after = snapshot()
    changed = [name for name, value in before['tables'].items()
               if name not in CMS_TABLES and after['tables'].get(name) != value]
    report = {'before': before, 'after': after, 'returncode': result.returncode,
              'stdout': result.stdout, 'stderr': result.stderr, 'changed_protected_tables': changed,
              'schema_unchanged': before['schema'] == after['schema'],
              'home_unchanged': before['home'] == after['home']}
    if result.returncode == 0:
        report['content'] = json.loads(result.stdout)
    RECEIPT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    assert result.returncode == 0, 'CMS import refused; inspect the preserved receipt'
    assert not changed, f'Concurrent collection or unexpected change: {changed}; inspect receipt'
    assert report['schema_unchanged'] and report['home_unchanged']
    assert after['integrity'] == [('ok',)] and not after['foreign_keys']
    assert len(report['content']['heads']) == 9
    print(json.dumps({'receipt': str(RECEIPT), 'heads': report['content']['heads'],
                      'protected_unchanged': True, 'home_unchanged': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
