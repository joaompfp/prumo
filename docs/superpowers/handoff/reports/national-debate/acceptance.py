"""Read models and preservation checks for the reviewed editorial collection."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

from html.parser import HTMLParser

from fastapi.testclient import TestClient

from app.main import create_app
from backoffice.cms import Cms
from ingest import cms as documents
from scripts.publish_cms_collection import install


class PageParser(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.headings = []
        self.links = []
        self.fields = set()
        self.payloads = []
        self._heading = None
        self._payload = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h1':
            self._heading = []
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag in ('input', 'select') and 'name' in attrs:
            self.fields.add(attrs['name'])
        if tag == 'script' and 'chart-data' in attrs.get('class', '').split():
            self._payload = []

    def handle_data(self, data):
        if self._heading is not None:
            self._heading.append(data)
        if self._payload is not None:
            self._payload.append(data)

    def handle_endtag(self, tag):
        if tag == 'h1' and self._heading is not None:
            self.headings.append(' '.join(''.join(self._heading).split()))
            self._heading = None
        if tag == 'script' and self._payload is not None:
            self.payloads.append(json.loads(''.join(self._payload)))
            self._payload = None


def fingerprint(path):
    result = {}
    with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro&readonly_shm=1', uri=True) as c:
        c.execute('BEGIN')
        for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            if name.startswith('sqlite_'):
                continue
            digest = hashlib.sha256()
            count = 0
            for row in c.execute('SELECT * FROM "' + name + '" ORDER BY rowid'):
                digest.update(json.dumps(row, ensure_ascii=False, separators=(',', ':'), default=str).encode() + b'\n')
                count += 1
            result[name] = {'rows': count, 'sha256': digest.hexdigest()}
        result['schema'] = hashlib.sha256(json.dumps(list(c.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name'))).encode()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    shutil.copy2(args.baseline, args.output)
    # This is an owned, offline copy. Keep its ordinary owner connection open so all
    # read-only service handles see canonical WAL/SHM; never recover sidecars on live data.
    owner = sqlite3.connect(args.output)
    owner.execute('PRAGMA journal_mode=WAL')
    owner.execute('SELECT name FROM sqlite_master LIMIT 1').fetchall()
    bundle = json.loads(args.bundle.read_text())
    before = fingerprint(args.output)
    cms = Cms(args.output, args.output)
    old_documents = {(kind, row['slug']): cms.get(kind, row['slug'])
                     for kind in ('page', 'chart') for row in cms.list(kind)}
    checks = []
    completed = False

    def check(name, value):
        checks.append({'name': name, 'passed': bool(value)})
        assert value, name

    try:
        installed = install(cms, bundle, actor='operator:acceptance',
                            note='Aceitação isolada do acervo', publish=True)
        check('whole collection published', installed['completed'] and all(row['status']=='published' for row in installed['documents']))
        first = fingerprint(args.output)
        repeated = install(cms, bundle, actor='operator:acceptance',
                           note='Repetição não substitui o operador', publish=True)
        check('rerun preserves every document and audit byte', first == fingerprint(args.output)
              and all(row['status']=='preserved' for row in repeated['documents']))
        check('all previous documents and histories unchanged', all(cms.get(*key)==body for key,body in old_documents.items()))
        client = TestClient(create_app(str(args.output)))
        for prefix in ('', '/dados'):
            headers = {'X-Forwarded-Prefix': prefix} if prefix else {}
            for entry in bundle['documents']:
                kind, slug = entry['kind'], entry['slug']
                stored = cms.get(kind, slug)
                check(f'{prefix} {kind}/{slug}: exact published CMS body', stored['published'] == documents.parse_body(kind, entry['body']))
                path = '/comparar/' + slug if kind == 'chart' else '/paginas/' + slug
                response = client.get(path, headers=headers)
                parsed = PageParser(response.text)
                check(f'{prefix} {path}: title and one heading', response.status_code==200
                      and parsed.headings==[entry['body']['title']])
                if kind == 'chart':
                    payloads = parsed.payloads
                    check(f'{prefix} {path}: all selected series drawn', len(payloads)==1
                          and len(payloads[0]['series']) == len(stored['published'].series_ids)
                          and len(payloads[0]['x']) > 1)
                    check(f'{prefix} {path}: public composition is not configurable', not parsed.fields.intersection({'series_a','s','escala'}))
                else:
                    preview = cms.preview(kind, slug)[1]
                    check(f'{prefix} {path}: no unavailable blocks', not preview.availability_note)
                    for href in parsed.links:
                        if href.startswith(prefix + '/caderno?'):
                            target = href[len(prefix):] if prefix else href
                            result = client.get(target, headers=headers)
                            check(f'{prefix} {slug}: native notebook link works', result.status_code==200
                                  and 'script' in result.text and 'chart-data' in result.text)
        debt = cms.preview('chart','credito-depositos-evolucao-base2015')[1]
        check('annual stocks exclude incomplete 2026', all(line.period_text=='2025' for line in debt.provenance))
        after = fingerprint(args.output)
        check('schema unchanged', before['schema']==after['schema'])
        check('all non-CMS tables unchanged', all(before[name]==after[name] for name in before if not name.startswith('cms_')))
        completed = True
    finally:
        receipt = {'completed': completed, 'passed': completed and all(row['passed'] for row in checks),
                   'checks': checks, 'before': before, 'after': fingerprint(args.output),
                   'expected_documents': len(bundle['documents'])}
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
        owner.close()
        print(json.dumps({'receipt':str(args.receipt),'completed':completed,
                          'passed':receipt['passed'],'checks':len(checks)}))


if __name__ == '__main__':
    main()
