"""Exercise unchanged CMS lifecycle against a separate copy of real data."""
import hashlib
import json
import re
import shutil
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app as public_app
from backoffice.app import create_app as admin_app
from tests.backoffice.test_cms_routes import page_form

root=Path('/home/joao/.hermes/cache/scratch/prumo-frontend-release')
db=root/'cms-cycle-corrected.sqlite3'
if db.exists():
    raise FileExistsError(db)
shutil.copy2(root/'acceptance.sqlite3',db)


def fingerprints():
    with sqlite3.connect(db.as_uri()+'?mode=ro&readonly_shm=1',uri=True) as c:
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if not r[0].startswith(('cms_','sqlite_'))]
        out={}
        for t in tables:
            digest=hashlib.sha256()
            for row in c.execute('SELECT * FROM "'+t+'" ORDER BY rowid'):
                digest.update(json.dumps(row,ensure_ascii=False,separators=(',',':'),default=str).encode()+b'\n')
            out[t]=digest.hexdigest()
        return out


before=fingerprints()
admin=TestClient(admin_app(db,Path('registry/core.yaml'),editorial_db_path=db),base_url='http://localhost',follow_redirects=False)
public=TestClient(public_app(str(db)))
headers={'Origin':'http://localhost'}
slug='ui-component-acceptance'
checks=[]
def check(name,value):
    checks.append({'name':name,'passed':bool(value)})
    assert value,name

complete=False
try:
    r=admin.post('/cms/new',data={'kind':'page','slug':slug,'title':'Ensaio dos componentes','introduction':'Conteúdo de aceitação isolado.','section':'economy','note':'Teste local'},headers=headers)
    check('create page',r.status_code==303)
    route='/cms/page/'+slug
    def version():
        text=admin.get(route).text
        return int(re.search(r'name="version" value="(\d+)"',text).group(1))
    blocks=[{'type':'text','text':'Texto editorial de aceitação.'},{'type':'card','series_id':'ine.hicp_yoy.PT'},{'type':'chart','chart_slug':'taxas-juro-credito-depositos'}]
    r=admin.post(route+'/save',data=page_form(version(),title='Ensaio dos componentes',blocks=blocks),headers=headers)
    check('save populated blocks',r.status_code==303)
    r=admin.get(route+'/preview')
    check('preview all components',r.status_code==200 and 'bootstrap-subset.css' in r.text and 'chart-data' in r.text)
    check('preview remains static',not re.search(r'<script[^>]+src=',r.text))
    check('draft stays private',public.get('/paginas/'+slug).status_code==404)
    r=admin.post(route+'/publish',data={'version':str(version()),'note':'Publicar ensaio isolado'},headers=headers)
    check('publish populated page',r.status_code==303)
    r=public.get('/paginas/'+slug)
    check('public reads published title and components',r.status_code==200 and 'Ensaio dos componentes' in r.text and 'btn btn-' in r.text and 'chart-data' in r.text)
    r=admin.post(route+'/unpublish',data={'version':str(version()),'note':'Retirar ensaio isolado'},headers=headers)
    check('unpublish page',r.status_code==303)
    check('publication withdrawn',public.get('/paginas/'+slug).status_code==404)
    # The CMS writer deliberately uses WAL. Prepare only this owned offline copy
    # after the writers have closed; readers must never recover a missing SHM.
    with sqlite3.connect(db) as offline_owner:
        assert offline_owner.execute('PRAGMA journal_mode=DELETE').fetchone()[0] == 'delete'
    check('all non-CMS tables unchanged',fingerprints()==before)
    complete=True
finally:
    out={'completed':complete,'passed':complete and all(c['passed'] for c in checks),'checks':checks,'protected_tables':len(before)}
    (root/'cms-cycle-corrected.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out))
