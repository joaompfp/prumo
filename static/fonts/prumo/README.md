# Prumo local typefaces

These are local, licensed subsets served from `static/fonts/prumo/`. There is no CDN, npm
runtime dependency or outbound font request. The CSS entry point is `static/css/fonts.css`.

## Files and licences

| File | Family / weight | Source package | Source file | SHA-256 (source) |
|---|---|---|---|---|
| `lato-regular.woff2` | Lato 400 | fonts-lato 2.015-1 | `/usr/share/fonts/truetype/lato/Lato-Regular.ttf` | `6f6940be0835c3ddec9199e5fc42be4cbc61ebcfd58c623fdf719366253f1780` |
| `lato-semibold.woff2` | Lato 600 | fonts-lato 2.015-1 | `/usr/share/fonts/truetype/lato/Lato-Semibold.ttf` | `2dc5d31e2cf1e29f3430eb2dfa1ba9911e08ee401b61dd12f40e0acb047a17a3` |
| `lato-bold.woff2` | Lato 700 | fonts-lato 2.015-1 | `/usr/share/fonts/truetype/lato/Lato-Bold.ttf` | `bf1b8130069b44b9148eeece35e5423bedac49777ba746615b826b8276574a7b` |
| `schola-regular.woff2` | TeX Gyre Schola 400 | fonts-texgyre 20180621-6 | `/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreschola-regular.otf` | `935b82e25f56b1d1276ca82793205e8ce254fbb37ebd38bedf7388cef21fbf44` |
| `schola-bold.woff2` | TeX Gyre Schola 700 | fonts-texgyre 20180621-6 | `/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreschola-bold.otf` | `988c7b2a0ff0eae77d1df3338751b3c47a5e759117734a375b8e7f9de80e698b` |

Licence texts: `OFL-1.1.txt` (Lato) and `GUST-FONT-LICENSE.txt` (TeX Gyre Schola). Readable copies remove only trailing whitespace; exact originals are preserved in the matching `.gz` archives, with original/copy hashes in `LICENCES.json`. Both
families permit embedding and redistribution under their stated terms. The subsets are
unmodified glyph selections from the installed files.

## Reproducible generation

Run from the repository root. The toolchain is FontTools 4.62.1 with Brotli 1.2.0 from the
system Python; it is build-time only and not a runtime dependency.

```bash
UNI='U+0000-00FF,U+0100-017F,U+2000-206F,U+20A0-20CF,U+2116,U+2122,U+2190-2193,U+2212,U+2264,U+2265'
pyftsubset /usr/share/fonts/truetype/lato/Lato-Regular.ttf \
  --output-file=static/fonts/prumo/lato-regular.woff2 --flavor=woff2 \
  --unicodes="$UNI" --layout-features='*' --no-hinting --desubroutinize \
  --name-IDs='*' --name-languages='*'
```

Repeat the same command with these source/output/name triples:

| Source | Output |
|---|---|
| `Lato-Semibold.ttf` | `lato-semibold.woff2` |
| `Lato-Bold.ttf` | `lato-bold.woff2` |
| `texgyreschola-regular.otf` | `schola-regular.woff2` |
| `texgyreschola-bold.otf` | `schola-bold.woff2` |

Two independent builds into isolated directories produced byte-identical files. Expected
output hashes and byte counts are in `MANIFEST.json`; verify with:

```bash
sha256sum static/fonts/prumo/*.woff2
```

The first line of a generated file is `wOF2`, which is also asserted by the repository tests.
The subset covers Latin-1, Latin Extended-A, general punctuation, currency, the Portuguese
quotation marks and ordinals, and the mathematical minus used by publisher tokens. Italic is
not shipped; the only italic use is a fallback empty-chart sentence, where browser synthesis is
acceptable.
