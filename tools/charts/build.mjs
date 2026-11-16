#!/usr/bin/env node
/* Reproducible local ECharts build for Prumo.
 *
 *   npm ci --prefix tools/charts --ignore-scripts --no-audit --no-fund
 *   node tools/charts/build.mjs
 *
 * Writes the committed runtime asset static/js/prumo-charts.min.js, its manifest, and the
 * upstream licence texts. Production copies static/ only: Node and npm stay out of the image.
 */
import { build } from 'esbuild';
import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', '..');
const outFile = join(root, 'static', 'js', 'prumo-charts.min.js');
const manifestFile = join(root, 'static', 'js', 'prumo-charts.manifest.json');
const licenceDir = join(root, 'static', 'js', 'licenses');

mkdirSync(licenceDir, { recursive: true });

await build({
  entryPoints: [join(here, 'src', 'adapter.js')],
  outfile: outFile,
  bundle: true,
  minify: true,
  format: 'iife',
  target: 'es2020',
  platform: 'browser',
  charset: 'utf8',
  legalComments: 'none',
  logLevel: 'warning',
});

const body = readFileSync(outFile);
const sha = createHash('sha256').update(body).digest('hex');
const gzip = gzipSync(body, { level: 9, mtime: 0 }).length;

const packages = {};
for (const name of ['echarts', 'zrender', 'tslib']) {
  packages[name] = JSON.parse(readFileSync(join(here, 'node_modules', name, 'package.json'),
                                           'utf8')).version;
}
const licences = {
  'echarts-APACHE-2.0.txt': join(here, 'node_modules', 'echarts', 'LICENSE'),
  'zrender-APACHE-2.0.txt': join(here, 'node_modules', 'zrender', 'LICENSE'),
  'tslib-0BSD.txt': join(here, 'node_modules', 'tslib', 'LICENSE.txt'),
};
for (const [target, source] of Object.entries(licences)) {
  copyFileSync(source, join(licenceDir, target));
}

const manifest = {
  asset: 'js/prumo-charts.min.js',
  sha256: sha,
  bytes: body.length,
  gzip_bytes: gzip,
  gzip_method: 'zlib level 9, mtime=0 (local measurement, not a transfer claim)',
  echarts: packages.echarts,
  zrender: packages.zrender,
  tslib: packages.tslib,
  esbuild: '0.25.12',
  entry: 'tools/charts/src/adapter.js',
  build: 'npm ci --prefix tools/charts --ignore-scripts --no-audit --no-fund && node tools/charts/build.mjs',
};
writeFileSync(manifestFile, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

writeFileSync(join(root, 'static', 'js', 'prumo-charts.NOTICE.txt'), [
  'Prumo chart bundle',
  `SHA-256: ${sha}`,
  `Bytes: ${body.length} (gzip level 9, mtime=0: ${gzip})`,
  `ECharts ${packages.echarts} - Apache License 2.0 - https://echarts.apache.org/`,
  `ZRender ${packages.zrender} - Apache License 2.0 - https://github.com/ecomfe/zrender`,
  `tslib ${packages.tslib} - 0BSD - https://github.com/Microsoft/tslib`,
  'Built with esbuild 0.25.12. Licence texts: static/js/licenses/.',
  'Rebuild: ' + manifest.build,
  '',
].join('\n'), 'utf8');

console.log(`built ${outFile}: ${body.length} bytes, ${sha.slice(0, 12)}, gzip ${gzip}`);
if (body.length > 650000 || gzip > 220000) {
  console.error('chart bundle exceeds the approved budget');
  process.exit(1);
}
