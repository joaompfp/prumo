# Prumo icon font

`prumo-icons.woff2` is a subset of Bootstrap Icons 1.11.3 (woff2 build published in the
`bootstrap-icons` npm package), pinned by version and reduced to the glyphs the Admin shell
and the public shell use. Bootstrap Icons is MIT licensed; the full licence text is in
`LICENSE.bootstrap-icons.txt`.

- Upstream: https://github.com/twbs/icons, package `bootstrap-icons@1.11.3`
- Source file: `font/fonts/bootstrap-icons.woff2` from that package
- Subset tool: `fonttools pyftsubset` with `--flavor=woff2 --layout-features='' --no-hinting`
- Subset size: 3.6 kB, 37 glyphs
- Local only: both the font and `static/css/icons.css` are served by the application; there
  is no CDN, no runtime font loader and no JavaScript involved in rendering an icon.

Glyph map (Bootstrap Icons name and Unicode private-use codepoint):

```
activity            U+F66B    archive             U+F10D
arrow-down          U+F128    arrow-left          U+F12F
arrow-right         U+F138    arrow-up            U+F148
bar-chart-line      U+F17C    box-arrow-up-right  U+F1C5
calculator          U+F1E0    calendar3           U+F214
check-circle        U+F26B    chevron-right       U+F285
clock-history       U+F292    cloud-upload        U+F2C0
copy                U+F759    database            U+F8C4
exclamation-triangle U+F33B   eye                 U+F341
file-earmark-text   U+F38B    flag                U+F3CC
graph-up            U+F3F2    grid                U+F3FC
hourglass-split     U+F41F    house-door          U+F423
inbox               U+F42D    info-circle         U+F431
journal-text        U+F444    layers              U+F45B
list-check          U+F473    list-task           U+F477
pencil-square       U+F4CA    plus-lg             U+F64D
search              U+F52A    shield-check        U+F52F
table               U+F5AA    trash               U+F5DE
x-lg                U+F659
```

Icons are decorative: each `<i class="icon ...">` carries `aria-hidden="true"` and every
action keeps a visible text label, so a blocked or unavailable font never removes meaning.
