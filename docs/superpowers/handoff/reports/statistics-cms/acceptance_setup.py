"""Isolated production-copy acceptance setup. Never opens production for writing."""
import hashlib
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path('/home/joao/projects/prumo-pipeline')
sys.path.insert(0, str(ROOT))
from backoffice.cms import Cms
from ingest.db import open_db
from presentation.catalog import pt

OUT = Path('/home/joao/.hermes/cache/scratch/prumo-cms-acceptance')
BASE = OUT / 'baseline-0018.sqlite3'
DB = OUT / 'acceptance-0019.sqlite3'
PROTECTED = ('source', 'series', 'observation', 'quarantine', 'derived_series',
             'derived_run', 'derived_observation', 'derived_event', 'verification',
             'verification_item', 'raw_fetch', 'dataset_run', 'editorial_page',
             'editorial_slot', 'editorial_event', 'event', 'scheduler_state', 'setting')


def fingerprint(path):
    c = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    result = {}
    for table in PROTECTED:
        h = hashlib.sha256()
        count = 0
        for row in c.execute(f'SELECT * FROM {table} ORDER BY rowid'):
            h.update(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode())
            h.update(b'\n')
            count += 1
        result[table] = {'rows': count, 'sha256': h.hexdigest()}
    c.close()
    return result


if __name__ == '__main__':
    assert not DB.exists(), 'Refuse to replace an acceptance database'
    before = fingerprint(BASE)
    shutil.copy2(BASE, DB)
    started = time.perf_counter()
    db = open_db(DB)
    migration_s = time.perf_counter() - started
    integrity = db.conn.execute('PRAGMA integrity_check').fetchone()[0]
    fk = db.conn.execute('PRAGMA foreign_key_check').fetchall()
    migrations = [r[0] for r in db.conn.execute('SELECT version FROM schema_migration ORDER BY version')]
    db.close()
    cms = Cms(DB, DB)
    kwargs = {'actor': 'acceptance-operator', 'note': 'Isolated acceptance only'}
    pair = pt.COMPARISONS['credito-e-taxa']
    chart = {'title': 'Juros e crédito à habitação', 'note': 'Escalas independentes; a sobreposição não demonstra causalidade.',
             'series_a': pair['series_a'], 'series_b': pair['series_b'],
             'derived_key': None, 'window': '10y', 'scale': 'dual', 'day': None}
    m = cms.create('chart', 'juros-credito', chart, **kwargs)
    cms.publish('chart', 'juros-credito', m['version'], **kwargs)
    page = {'title': 'Juros e crédito', 'introduction': 'Uma página dinâmica com estatísticas oficiais. Texto de ensaio, não publicado em produção.',
            'section': 'economy', 'blocks': [
                {'type': 'text', 'text': 'A Euribor e o stock de crédito descrevem dimensões diferentes.'},
                {'type': 'card', 'series_id': pair['series_a'], 'derived_key': None},
                {'type': 'chart', 'chart_slug': 'juros-credito'}]}
    m = cms.create('page', 'juros-e-credito', page, **kwargs)
    cms.publish('page', 'juros-e-credito', m['version'], **kwargs)
    saved = cms.get('page', 'juros-e-credito')
    old_rid = saved['meta']['draft_revision_id']
    page['title'] = 'Juros e crédito - rascunho alterado'
    m = cms.save('page', 'juros-e-credito', saved['meta']['version'], page, **kwargs)
    assert cms.get('page', 'juros-e-credito')['published'].title == 'Juros e crédito'
    m = cms.restore('page', 'juros-e-credito', m['version'], old_rid, **kwargs)
    m = cms.publish('page', 'juros-e-credito', m['version'], **kwargs)
    cms.duplicate('page', 'juros-e-credito', 'juros-duplicado', version=m['version'], **kwargs)
    after = fingerprint(DB)
    assert before == after, [k for k in before if before[k] != after[k]]
    started = time.perf_counter()
    choices = cms.choices()
    choices_s = time.perf_counter() - started
    report = {'migration_s': migration_s, 'integrity': integrity, 'fk_violations': len(fk),
              'migration': migrations[-1], 'protected_tables_unchanged': before == after,
              'protected_tables': before, 'choices': len(choices), 'choices_s': choices_s,
              'workflow': 'create chart, publish, create page, publish, private edit, restore, republish, duplicate',
              'acceptance_db': str(DB), 'base_bytes': BASE.stat().st_size,
              'screen_reader': 'not exercised by a human', 'production_changed': False}
    (OUT / 'database-acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'protected_tables'}, ensure_ascii=False, indent=2))
