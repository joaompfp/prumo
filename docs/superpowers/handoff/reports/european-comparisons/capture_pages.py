"""Capture local HTML evidence and label concurrent development timings."""
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[5]
BASE = os.environ.get('PRUMO_QA_URL', 'http://127.0.0.1:8099')
if not BASE.startswith('http://127.0.0.1:'):
    raise ValueError('Local acceptance only')
OUT = Path(__file__).parent / 'receipts'
OUT.mkdir(exist_ok=True)
paths = ['/comparar', '/comparar/paises/eletricidade-domestica',
         '/comparar/paises/pib-por-habitante', '/comparar/paises/divida-publica']
report = {'context': 'Local production-copy server; full offline test suite running concurrently.',
          'samples': 20, 'paths': [], 'raw_bodies': []}
for route in paths:
    with urlopen(BASE + route, timeout=10) as response:
        if response.status != 200:
            raise ValueError(response.status)
        body = response.read()
        headers = dict(response.headers)
    name = route.rsplit('/', 1)[-1] + '.html.gz'
    target = OUT / name
    if target.exists():
        raise FileExistsError(target)
    target.write_bytes(gzip.compress(body, mtime=0))
    assert gzip.decompress(target.read_bytes()) == body
    report['raw_bodies'].append({'route': route, 'status': 200, 'headers': headers,
                                'file': name, 'bytes': len(body),
                                'sha256': hashlib.sha256(body).hexdigest()})
    times = []
    for _ in range(report['samples']):
        start = time.perf_counter()
        with urlopen(BASE + route, timeout=10) as response:
            assert response.status == 200
            response.read()
        times.append((time.perf_counter() - start) * 1000)
    report['paths'].append({'route': route, 'median_ms': statistics.median(times),
                            'p95_ms': sorted(times)[math.ceil(.95 * len(times)) - 1]})
(OUT / 'http-and-timings.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))
