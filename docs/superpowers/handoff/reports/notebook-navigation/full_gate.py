"""Controller offline gate with an exhaustive collected-node manifest and isolated workers.

No marker expression is overridden. Collection uses the same `tests -q` scope as the normal
command; pytest.ini excludes network tests. Every selected node runs exactly once. Workers
keep each module together, with independent temporary/cache directories and JUnit receipts.
"""
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(os.environ['PRUMO_GATE_OUT']).resolve()
OUT.mkdir(parents=True, exist_ok=False)
os.chdir(ROOT)


class Population:
    def __init__(self):
        self.nodes = []
        self.excluded = []

    def pytest_collection_finish(self, session):
        self.nodes = [item.nodeid for item in session.items]

    def pytest_deselected(self, items):
        self.excluded.extend(item.nodeid for item in items)


population = Population()
with (OUT / 'collection.log').open('w') as log:
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        result = pytest.main(['tests', '-q', '--collect-only'], plugins=[population])
if result != 0 or not population.nodes:
    raise RuntimeError(f'Collection failed: {result}')
assert len(population.nodes) == len(set(population.nodes))
modules: dict[str, list[str]] = {}
for node in population.nodes:
    modules.setdefault(node.split('::')[0], []).append(node)
# Greedy balanced module assignment keeps fixtures together without changing test order inside
# a module. Three workers are deliberately bounded, rather than spawning one per host CPU.
buckets: list[list[str]] = [[], [], []]
for module in sorted(modules, key=lambda name: (-len(modules[name]), name)):
    target = min(range(len(buckets)), key=lambda index: len(buckets[index]))
    buckets[target].extend(modules[module])
assert sorted(node for group in buckets for node in group) == sorted(population.nodes)
assert len(set(node for group in buckets for node in group)) == len(population.nodes)
manifest = {'selected': population.nodes, 'deselected': population.excluded, 'workers': buckets}
manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode()
(OUT / 'population.json').write_bytes(manifest_bytes)

processes = []
logs = []
for index, nodes in enumerate(buckets):
    log = (OUT / f'worker-{index}.log').open('w')
    logs.append(log)
    command = [sys.executable, '-m', 'pytest', *nodes, '-q',
               f'--basetemp={OUT / ("temporary-" + str(index))}',
               '-o', f'cache_dir={OUT / ("cache-" + str(index))}',
               f'--junitxml={OUT / ("worker-" + str(index) + ".xml")}']
    processes.append(subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT))
statuses = [process.wait() for process in processes]
for log in logs:
    log.close()
summary = {'scope': 'full selected offline population, three isolated module-preserving partitions',
           'selected': len(population.nodes), 'deselected': len(population.excluded),
           'population_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
           'statuses': statuses, 'workers': []}
for index, nodes in enumerate(buckets):
    xml = ET.parse(OUT / f'worker-{index}.xml').getroot()
    suites = xml.findall('testsuite') if xml.tag == 'testsuites' else [xml]
    totals = {key: sum(int(suite.get(key, '0')) for suite in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    assert totals['tests'] == len(nodes), (index, totals, len(nodes))
    summary['workers'].append({'index': index, 'nodes': len(nodes), **totals})
summary['passed'] = sum(row['tests']-row['failures']-row['errors']-row['skipped'] for row in summary['workers'])
summary['success'] = all(code == 0 for code in statuses) and summary['passed'] == summary['selected']
(OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(json.dumps(summary, ensure_ascii=False, indent=2))
raise SystemExit(0 if summary['success'] else 1)
