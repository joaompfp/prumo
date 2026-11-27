"""Prove the real new documents are editable via existing labelled browser controls."""
import json
import runpy
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from app.main import create_app
from backoffice.cms import Cms

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).parent
DB = Path('/home/joao/.hermes/cache/scratch/prumo-debate-20261127/authoring.sqlite3')
manifest = json.loads((ROOT/'docs/editorial/debate-nacional-2026-11-27/collection.json').read_text())
fingerprint = runpy.run_path(str(HERE/'acceptance.py'), run_name='acceptance_helpers')['fingerprint']
before = fingerprint(DB)
cms = Cms(DB, DB)
old_home = cms.get('page', 'inicio')
checks = []
completed = False


def check(name, result):
    checks.append({'name':name,'passed':bool(result)})
    assert result, name


try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path='/home/joao/.cache/ms-playwright/chromium-1255/chrome-linux64/chrome')
        page = browser.new_page(viewport={'width':1440,'height':1000})
        for entry in manifest['documents']:
            kind, slug, body = entry['kind'], entry['slug'], entry['body']
            response = page.goto('http://127.0.0.1:8180/cms/'+kind+'/'+slug)
            check(f'{kind}/{slug}: editor loaded', response.status==200)
            check(f'{kind}/{slug}: authored title populated', page.locator('input[name="title"]').input_value()==body['title'])
            if kind=='chart':
                expected = [body['series_a'],body.get('series_b')]+body.get('series_extra',[])
                names = ['series_a','series_b']+[f'series_extra_{i}' for i in range(4)]
                for i, sid in enumerate(expected):
                    check(f'{slug}: selected series {i}', page.locator(f'select[name="{names[i]}"]').input_value()==sid)
                    check(f'{slug}: axis {i}', page.locator(f'select[name="axis_{i}"]').input_value()==str(body['axes'][i]))
            check(f'{kind}/{slug}: saved draft preview', page.goto('http://127.0.0.1:8180/cms/'+kind+'/'+slug+'/preview').status==200)
            check(f'{kind}/{slug}: preview is non-executable', page.locator('script[src]').count()==0)
        slug='euribor-tres-seis-doze-meses'
        original = cms.get('chart',slug)
        doc = original['published']
        page.goto('http://127.0.0.1:8180/cms/chart/'+slug)
        page.locator('[name="series_a"]').select_option(doc.series_b)
        page.locator('[name="series_b"]').select_option(doc.series_a)
        page.locator('#draft-note').fill('Trocar a ordem no ensaio isolado')
        page.locator('button[name="op"][value="save"]').click()
        draft = cms.get('chart',slug)
        check('native save changes only the draft', draft['draft'].series_a==doc.series_b and draft['published']==doc)
        page.goto('http://127.0.0.1:8180/cms/chart/'+slug+'/preview')
        check('changed private preview is populated', page.locator('script.chart-data').count()==1)
        page.goto('http://127.0.0.1:8180/cms/chart/'+slug)
        page.locator('#publish-note').fill('Publicar a ordem no ensaio isolado')
        page.on('dialog', lambda dialog: dialog.accept())
        page.locator('form[action$="/publish"] button').click()
        published = cms.get('chart',slug)
        check('native publish uses changed series order', published['published'].series_ids==(doc.series_b,doc.series_a,*doc.series_extra))
        public = TestClient(create_app(str(DB))).get('/comparar/'+slug)
        check('reader receives changed publication', public.status_code==200 and doc.title in public.text)
        check('homepage unchanged through real browser writes', cms.get('page','inicio')==old_home)
        after = fingerprint(DB)
        check('all non-CMS tables unchanged through authoring', all(before[key]==after[key] for key in before if not key.startswith('cms_')))
        browser.close()
    completed = True
finally:
    receipt={'completed':completed,'passed':completed and all(c['passed'] for c in checks),'checks':checks}
    (HERE/'authoring-browser.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'completed':completed,'passed':receipt['passed'],'checks':len(checks)}))
