"""Matched-copy server benchmarks, outside the app/runtime."""
import json
import sqlite3
import statistics
import sys
import time
from pathlib import Path

code, db_path, out_path = sys.argv[1:4]
sys.path.insert(0, code)
from fastapi.testclient import TestClient
from app.main import create_app

c = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
top = c.execute("SELECT o.series_id,count(*) AS n FROM served_observation o "
                "JOIN series s ON s.id=o.series_id "
                "WHERE o.kind='fetched' AND s.frequency!='PT15M' AND s.role='primary' "
                "GROUP BY o.series_id ORDER BY n DESC LIMIT 3").fetchall()
c.close()
paths = ['/', '/comparar/credito-e-taxa', '/comparar/euribor-e-inflacao',
         '/series/eredes.production_total.PT', '/series/ine.hicp_yoy.PT']
paths += ['/series/' + row[0] for row in top if '/series/' + row[0] not in paths]
if (Path(code) / 'app/cms_reads.py').exists():
    paths += ['/paginas', '/paginas/juros-e-credito', '/graficos/juros-credito']
report = {'code': code, 'db': db_path, 'top_noninterval_populations': top, 'samples': 20,
          'routes': {}, 'method': 'TestClient GET including templates and ASGI; same host/copy; no HTTP compression'}
with TestClient(create_app(db_path)) as client:
    for path in paths:
        warm = client.get(path)
        assert warm.status_code == 200, (path, warm.status_code)
        durations = []
        for _ in range(20):
            started = time.perf_counter()
            response = client.get(path)
            durations.append((time.perf_counter() - started) * 1000)
            assert response.status_code == 200
        report['routes'][path] = {'median_ms': statistics.median(durations),
                                 'p95_ms': sorted(durations)[18], 'html_bytes': len(response.content)}
Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))
