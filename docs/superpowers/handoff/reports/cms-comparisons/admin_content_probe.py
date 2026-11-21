"""Read back the actual populated Admin editors after the content import, without mutations."""
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


class Selected(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.values = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'select':
            self.current = attrs.get('name')
        if tag == 'option' and self.current:
            self.values.setdefault(self.current, attrs.get('value', ''))
            if 'selected' in attrs:
                self.values[self.current] = attrs.get('value', '')
    def handle_endtag(self, tag):
        if tag == 'select':
            self.current = None


def main():
    root = Path('/home/joao/prumo-operations/cms-comparisons-release-20261121')
    report = json.loads((root/'content.json').read_text())['content']
    inspection = json.loads(subprocess.check_output(['docker','inspect','prumo-backoffice']))[0]
    env = dict(item.split('=',1) for item in inspection['Config']['Env'] if '=' in item)
    headers = {'Host':'joao.date','X-Forwarded-Prefix':'/dados/admin',
               'X-Prumo-Proxy-Secret':env['PRUMO_ADMIN_PROXY_SECRET'],
               'Remote-User':env.get('PRUMO_ADMIN_USER','joao')}
    rows = []
    for head in report['heads']:
        route = '/cms/chart/' + head['slug']
        with urlopen(Request('http://100.118.19.6:8089'+route,headers=headers),timeout=30) as response:
            html = response.read().decode()
            assert response.status == 200
        parser = Selected()
        parser.feed(html)
        names = ['series_a','series_b',*[f'series_extra_{index}' for index in range(4)]]
        actual = [parser.values.get(name,'') for name in names]
        assert tuple(value for value in actual if value) == tuple(head['series']),head['slug']
        axes = [parser.values[f'axis_{index}'] for index,value in enumerate(actual) if value]
        assert axes == [str(axis) for axis in head['axes']],head['slug']
        assert parser.values['comparison_group'] == head['category']
        assert all(f'name="axis_{index}"' in html for index in range(6))
        assert f'action="/dados/admin/cms/chart/{head["slug"]}/save"' in html
        assert f'action="/dados/admin/cms/chart/{head["slug"]}/publish"' in html
        rows.append({'slug':head['slug'],'selected_series':actual,'selected_axes':axes,
                     'category':head['category'],'status':200})
    (root/'admin-content-readback.json').write_text(json.dumps({'editors':rows},indent=2)+'\n')
    print(json.dumps({'editors_verified':len(rows),'all_series_axes_categories_match':True}))


if __name__ == '__main__':
    main()
