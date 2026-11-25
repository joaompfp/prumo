"""Read-only exact-value and export invariants for a presentation-only release."""
import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen


class Payload(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and 'chart-data' in attrs.get('class', '').split():
            self.active = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--baseline', type=Path)
    args = p.parse_args()
    result = {'completed': False, 'passed': False, 'cases': {}}
    paths = (
        '/series/worldbank.life_expectancy.DE',
        '/series/worldbank.trade_balance_pct_gdp.DE',
        '/calculadas/derived.ipi_seasonal_cae_TOT.PT.yoy_change_pct',
        '/comparar/taxas-juro-credito-depositos',
    )
    try:
        for base in ('https://cae.joao.date', 'https://joao.date/dados'):
            for path in paths:
                with urlopen(base + path, timeout=30) as response:
                    assert response.status == 200
                    doc = Payload()
                    doc.feed(response.read().decode())
                assert doc.parts, base + path
                payload = json.loads(''.join(doc.parts))
                assert payload['y'], base + path
                # Everything but display prose is read back exactly as before installation.
                result['cases'][base + path] = {
                    'geometry_sha256': digest(json.dumps(payload['y'], separators=(',', ':')).encode()),
                    'point_rows': len(payload['y']),
                }
                if path.startswith(('/series/', '/calculadas/')):
                    with urlopen(base + path + '.csv', timeout=30) as response:
                        assert response.status == 200
                        raw = response.read()
                    result['cases'][base + path]['csv_sha256'] = digest(raw)
                    result['cases'][base + path]['csv_bytes'] = len(raw)
        if args.baseline:
            old = json.loads(args.baseline.read_text())
            assert old['passed'] and old['completed']
            assert result['cases'] == old['cases'], 'A plotted coordinate or exact CSV changed'
        result['completed'] = True
        result['passed'] = True
    finally:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'passed': result['passed'], 'cases': len(result['cases'])}))


if __name__ == '__main__':
    main()
