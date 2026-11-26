"""Preserve plotted coordinates and exact CSV tokens across the responsive inspection release."""
import argparse
import gzip
import hashlib
import json
import re
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    cases = {}
    for b, base in enumerate(('https://cae.joao.date', 'https://joao.date/dados')):
        for i, path in enumerate(('/series/worldbank.life_expectancy.DE', '/series/worldbank.trade_balance_pct_gdp.DE', '/calculadas/derived.ipi_seasonal_cae_TOT.PT.yoy_change_pct', '/comparar/taxas-juro-credito-depositos')):
            with urlopen(base + path, timeout=30) as response:
                assert response.status == 200
                doc = Payload()
                doc.feed(response.read().decode())
            payload = json.loads(''.join(doc.parts))
            assert payload['y']
            case = {'geometry_sha256': hashlib.sha256(json.dumps(payload['y'], separators=(',', ':')).encode()).hexdigest(), 'points': len(payload['y'])}
            if path.startswith(('/series/', '/calculadas/')):
                with urlopen(base + path + '.csv', timeout=30) as response:
                    assert response.status == 200
                    raw = response.read()
                lines = raw.decode('utf-8-sig').splitlines(keepends=True)
                clocks = [line for line in lines if re.fullmatch(r'Exportado a \d{2}/\d{2}/\d{4}, \d{2}:\d{2} UTC\r?\n?', line)]
                assert len(clocks) == 1
                normalized = ''.join(line for line in lines if line not in clocks).encode()
                case['csv_except_export_clock_sha256'] = hashlib.sha256(normalized).hexdigest()
                name = args.output.with_name(args.output.stem + f'-{b}-{i}.csv.gz')
                name.write_bytes(gzip.compress(raw, mtime=0))
                assert gzip.decompress(name.read_bytes()) == raw
            cases[base + path] = case
    result = {'passed': True, 'cases': cases}
    if args.baseline:
        previous = json.loads(args.baseline.read_text())
        assert previous['passed'] and previous['cases'] == cases
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'routes': len(cases), 'csv': sum('csv_except_export_clock_sha256' in c for c in cases.values())}))


if __name__ == '__main__':
    main()
