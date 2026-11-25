"""Compare unchanged original coordinates/exports across a presentation-only release."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

BASES = ('https://cae.joao.date', 'https://joao.date/dados')
PATHS = ('/series/worldbank.life_expectancy.DE',
         '/series/worldbank.trade_balance_pct_gdp.DE',
         '/calculadas/derived.ipi_seasonal_cae_TOT.PT.yoy_change_pct',
         '/comparar/taxas-juro-credito-depositos', '/comparar/eletricidade-domestica')
CLOCK = re.compile(rb'(?m)^Exportado a (\d{2}/\d{2}/\d{4}, \d{2}:\d{2} UTC)\r?$')


class Payload(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self.active = tag == 'script' and 'chart-data' in (dict(attrs).get('class') or '').split()

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def get(url):
    with urlopen(url, timeout=30) as response:
        assert response.status == 200, url
        return response.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = {'completed': False, 'passed': False, 'cases': {}, 'at': datetime.now(timezone.utc).isoformat()}
    try:
        for host_index, base in enumerate(BASES):
            for path_index, path in enumerate(PATHS):
                document = Payload()
                document.feed(get(base + path).decode())
                payload = json.loads(''.join(document.parts))
                assert payload['y'], base + path
                case = {'coordinates_sha256': digest(json.dumps(payload['y'], separators=(',', ':')).encode()),
                        'point_rows': len(payload['y'])}
                if path.startswith(('/series/', '/calculadas/')):
                    raw = get(base + path + '.csv')
                    assert len(CLOCK.findall(raw)) == 1, 'Single export clock required'
                    (args.output / f'{host_index}-{path_index}.csv').write_bytes(raw)
                    case['original_csv_sha256'] = digest(raw)
                    case['csv_without_export_clock_sha256'] = digest(CLOCK.sub(b'Exportado a <clock>', raw))
                result['cases'][base + path] = case
        assert len(result['cases']) == len(BASES) * len(PATHS)
        if args.baseline:
            before = json.loads(args.baseline.read_text())
            assert before['passed'] and before['completed']
            assert set(before['cases']) == set(result['cases'])
            for route, current in result['cases'].items():
                previous = before['cases'][route]
                assert current['coordinates_sha256'] == previous['coordinates_sha256'], route
                assert current['point_rows'] == previous['point_rows'], route
                if 'csv_without_export_clock_sha256' in current:
                    assert current['csv_without_export_clock_sha256'] == previous['csv_without_export_clock_sha256'], route
        result['completed'] = True
        result['passed'] = True
    finally:
        (args.output / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'passed': result['passed'], 'cases': len(result['cases'])}))


if __name__ == '__main__':
    main()
