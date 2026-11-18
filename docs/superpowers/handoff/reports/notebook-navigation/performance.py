"""Measure real notebook HTML/preparation costs without writes or external requests."""
import gzip
import hashlib
import json
import re
import statistics
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx

BASE = 'http://127.0.0.1:8107'
OUT = Path(__file__).parent / 'receipts' / 'performance.json'
GROUP = [f'bportugal.{name}.{geo}' for name, geo in (
    ('euribor_1m', 'EA'), ('euribor_3m', 'EA'), ('euribor_6m', 'EA'),
    ('euribor_12m', 'EA'), ('pt_10y', 'PT'), ('de_10y', 'DE'))]
paths = [('/', 'home'),
         ('/caderno?' + urlencode([('s', side) for side in GROUP]), 'six-default-10y'),
         ('/caderno?' + urlencode([('s', side) for side in GROUP] + [('janela', 'max')]), 'six-max'),
         ('/caderno?s=ine.hicp_yoy.PT&s=ine.unemployment_monthly.PT', 'two-default'),
         ('/caderno?s=eredes.production_market.PT&s=eredes.production_special.PT', 'interval-day')]
report: dict = {'base': BASE, 'scope': 'isolated production copy, sample groups only, concurrent controller suite', 'rows': []}
with httpx.Client(base_url=BASE, timeout=60) as client:
    for path, name in paths:
        for _ in range(2):
            client.get(path).raise_for_status()
        elapsed = []
        response: httpx.Response | None = None
        for _ in range(20):
            start = time.perf_counter()
            response = client.get(path)
            response.raise_for_status()
            elapsed.append((time.perf_counter()-start)*1000)
        assert response is not None
        match = re.search(r'<script type="application/json" class="chart-data">(.*?)</script>', response.text, re.S)
        payload = json.loads(match.group(1)) if match else None
        if name.startswith('six-'):
            assert payload is not None and len(payload['series']) == 6
        row = {'name': name, 'path': path, 'requests': len(elapsed),
               'median_ms': round(statistics.median(elapsed), 3),
               'p95_ms': round(sorted(elapsed)[18], 3), 'html_bytes': len(response.content),
               'local_gzip_bytes': len(gzip.compress(response.content, mtime=0)),
               'sha256': hashlib.sha256(response.content).hexdigest(),
               'series': len(payload['series']) if payload else 0,
               'points': len(payload['x']) if payload else 0}
        report['rows'].append(row)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))
