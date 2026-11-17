"""Reproduce pinned local font subsets without changing shipped files."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[5]
FONTS = ROOT / 'static/fonts/prumo'
manifest = json.loads((FONTS / 'MANIFEST.json').read_text())
report = {'toolchain': manifest['generated_by'], 'fonts': {}}
with tempfile.TemporaryDirectory(prefix='prumo-font-verify-',dir='/home/joao/.hermes/cache/scratch') as temporary:
    for name, info in manifest['files'].items():
        source = Path(info['source'])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == info['source_sha256'], name
        output = Path(temporary) / name
        subprocess.run(['/usr/bin/python3','-m','fontTools.subset',str(source),
                        '--output-file='+str(output),'--flavor=woff2',
                        '--unicodes='+manifest['unicode_ranges'],"--layout-features=*",
                        '--no-hinting','--desubroutinize','--name-IDs=*','--name-languages=*'],
                       check=True,capture_output=True)
        body = output.read_bytes()
        assert body == (FONTS / name).read_bytes(), name
        report['fonts'][name] = {'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'reproduced':True}
print(json.dumps(report,indent=2))
