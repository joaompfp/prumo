"""Archive exact test receipts and verify lossless compression after the final suite."""
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[5]
SOURCE = Path('/home/joao/.hermes/cache/scratch/prumo-legibility')
OUT = Path(__file__).resolve().parent
logs = ['scoped-integration-initial.log','failing-golden-checks.log','browser-initial.log',
        'browser-final.log','full-suite-final.log']
full = (SOURCE / 'full-suite-final.log').read_text()
summary = re.search(r'(\d+) passed, (\d+) deselected, (\d+) warnings in ([0-9.]+)s',full)
if summary is None or re.search(r'\d+ failed|ERROR collecting',full):
    raise RuntimeError('No successful completed suite receipt')
receipt = {
    'baseline':'6f851d4a5527b32613a434c1690e1228c70b7dd8',
    'installed_runtime_unchanged':'14f845ec2ca006fa992c460fd2af579940ac28bd',
    'full_suite':{'passed':int(summary[1]),'deselected':int(summary[2]),
                  'warnings':int(summary[3]),'seconds':float(summary[4]),'exit_code':0},
    'hosted_ci':'not run for pipeline-rebuild; workflow targets main and pull requests',
    'logs':{},'screens':{},
}
for name in logs:
    body = (SOURCE / name).read_bytes()
    encoded = gzip.compress(body,mtime=0)
    path = OUT / 'logs' / (name+'.gz')
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(encoded)
    assert gzip.decompress(path.read_bytes()) == body
    receipt['logs'][str(path.relative_to(ROOT))] = {
        'raw_bytes':len(body),'raw_sha256':hashlib.sha256(body).hexdigest(),
        'gzip_sha256':hashlib.sha256(encoded).hexdigest(),
    }
for directory in ('browser','browser-final'):
    for path in sorted((OUT / directory).glob('*.png')):
        body = path.read_bytes()
        receipt['screens'][str(path.relative_to(ROOT))] = {
            'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),
        }
report = json.loads((OUT/'browser-final/acceptance.json').read_text())
assert report['complete'] and all(check['passed'] for check in report['checks'])
receipt['browser']={'checks':len(report['checks']),'type_samples':len(report['ratios']),
                    'minimum_ratio':min(sample['ratio'] for sample in report['ratios']),
                    'protected_tables':len(report['protected_before']),
                    'errors':report['errors'],'warnings':report['warnings'],
                    'external':report['external']}
print(json.dumps(receipt,ensure_ascii=False,indent=2))
