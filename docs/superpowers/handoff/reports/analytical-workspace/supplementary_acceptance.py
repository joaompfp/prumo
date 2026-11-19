"""Additional six-side, painted point, type and matched-baseline checks on localhost only."""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import expect, sync_playwright

BASE = 'http://127.0.0.1:8129'
OLD = 'http://127.0.0.1:8128'
OUT = Path(os.environ['PRUMO_QA_OUT'])
OUT.mkdir(parents=True, exist_ok=True)
REPORT: dict = {'checks': [], 'comparisons': [], 'errors': []}
PAIR = ['ine.hicp_yoy.PT', 'ine.unemployment_monthly.PT']
SIX = PAIR + ['bportugal.euribor_1m.EA', 'bportugal.euribor_3m.EA', 'bportugal.euribor_6m.EA', 'bportugal.euribor_12m.EA']


def check(name, value):
    REPORT['checks'].append({'name': name, 'passed': bool(value)})
    assert value, name


def address(ids):
    return '/caderno?' + urlencode([('s', s) for s in ids])


def exact(payload, point):
    return payload['periods'][point] + ' - ' + '; '.join(f'{side["title"]}: {payload["display"][point][i]}' for i, side in enumerate(payload['series']))


def box(page):
    return page.locator('.chart-canvas').evaluate('''e=>{const r=e.getBoundingClientRect(); return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height,scrollY}}''')


def grid(page):
    return page.locator('.chart-canvas canvas').evaluate('''c => {
      const ctx=c.getContext('2d',{willReadFrequently:true});
      const d=ctx.getImageData(0,0,c.width,c.height).data;
      const probe=document.createElement('canvas').getContext('2d',{willReadFrequently:true});
      probe.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--rule').trim();
      probe.fillRect(0,0,1,1); const t=probe.getImageData(0,0,1,1).data;
      let left=0,right=0,best=0;
      for(let y=0;y<c.height;y++){let start=-1;
        for(let x=0;x<=c.width;x++){const i=(y*c.width+x)*4;
          const yes=x<c.width&&d[i+3]>100&&Math.abs(d[i]-t[0])<5&&Math.abs(d[i+1]-t[1])<5&&Math.abs(d[i+2]-t[2])<5;
          if(yes&&start<0)start=x;
          if(!yes&&start>=0){if(x-start>best){best=x-start;left=start;right=x-1;}start=-1;}
        }
      }
      const r=c.getBoundingClientRect();return {left:r.x+left*r.width/c.width,right:r.x+right*r.width/c.width,y:r.y+r.height/2,valid:best>c.width/3};
    }''')


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',args=['--no-sandbox'])
        ctx = browser.new_context()
        p = ctx.new_page()
        p.on('pageerror',lambda e:REPORT['errors'].append(str(e)))
        for width,height in ((390,844),(1440,1000),(1920,1080),(3774,1870)):
            p.set_viewport_size({'width':width,'height':height})
            entries = {}
            for name,base in (('before',OLD),('after',BASE)):
                r = p.goto(base+address(PAIR))
                assert r is not None and r.status==200
                p.evaluate('document.fonts.ready')
                p.locator('.chart-enhanced canvas').wait_for()
                p.evaluate('window.scrollTo(0,0)')
                entries[name] = box(p)
                payload = json.loads(p.locator('script.chart-data').inner_text())
                entries[name]['payload_sha256'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                entries[name]['svg_sha256'] = hashlib.sha256(p.locator('.chart-shell svg.chart').evaluate('e=>e.outerHTML').encode()).hexdigest()
                entries[name]['table_sha256'] = hashlib.sha256(p.locator('.table-details table').evaluate('e=>e.outerHTML').encode()).hexdigest()
                entries[name]['type'] = p.locator('body,.site-nav > a,.site-header input,.chart-readout').evaluate_all('es=>es.map(e=>({role:e.className||e.tagName,size:getComputedStyle(e).fontSize}))')
                if name=='after':
                    check('neutral first-view capture '+str(width), p.evaluate('scrollY')==0)
                    p.screenshot(path=str(OUT/f'notebook-{width}.png'))
            check('functional roles unchanged '+str(width),entries['before']['type']==entries['after']['type'])
            for key in ('payload_sha256','svg_sha256','table_sha256'):
                check('same snapshot '+key+' '+str(width),entries['before'][key]==entries['after'][key])
            REPORT['comparisons'].append({'width':width,'height':height,**entries})
        for width in (320,390,768,1440,3774):
            p.set_viewport_size({'width':width,'height':1000})
            p.goto(BASE+address(SIX))
            p.locator('.chart-enhanced canvas').wait_for()
            payload = json.loads(p.locator('script.chart-data').inner_text())
            check('six sides '+str(width),len(payload['series'])==6 and p.locator('.notebook-chart-sources li').count()==6)
            check('all names and exact table '+str(width),p.locator('.legend li').count()==6 and p.locator('.table-details tbody tr').count()==len(payload['x']))
            check('six without page overflow '+str(width),p.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        for width,mobile in ((1440,False),(390,True)):
            context = browser.new_context(viewport={'width':width,'height':1000},has_touch=mobile,is_mobile=mobile)
            page = context.new_page()
            page.goto(BASE+address(PAIR))
            page.locator('.chart-enhanced canvas').wait_for()
            page.locator('.chart-canvas').scroll_into_view_if_needed()
            payload = json.loads(page.locator('script.chart-data').inner_text())
            bounds = grid(page)
            check('painted grid '+str(width),bounds['valid'])
            for point in (0,len(payload['x'])//2,len(payload['x'])-1):
                x=bounds['left']+(bounds['right']-bounds['left'])*(payload['x'][point]-payload['x'][0])/(payload['x'][-1]-payload['x'][0])
                if mobile: page.touchscreen.tap(x,bounds['y'])
                else: page.mouse.move(x,bounds['y'])
                expect(page.locator('.chart-readout')).to_have_text(exact(payload,point))
                check('painted exact '+str(width)+'/'+str(point),True)
            check('vertical touch scroll preserved '+str(width),page.locator('.chart-canvas').evaluate('e=>getComputedStyle(e).touchAction')=='pan-y')
            context.close()
        p.set_viewport_size({'width':720,'height':500})
        p.goto(BASE+address(PAIR))
        check('200 percent equivalent reflow',p.evaluate('document.documentElement.scrollWidth<=innerWidth'))
        check('no page errors',not REPORT['errors'])
        browser.close()


try:
    run()
except Exception as exc:
    REPORT['failure']=str(exc)
    raise
finally:
    (OUT/'supplementary.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))
    print(json.dumps({'checks':len(REPORT['checks']),'passed':sum(c['passed'] for c in REPORT['checks']),'failure':REPORT.get('failure'),'output':str(OUT)},ensure_ascii=False))
