"""Computed contrast on the legibility candidate, using real toolkit cascade and assets."""
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[5]
BASE = os.environ.get("PRUMO_QA_URL", "http://127.0.0.1:8118")
OUT = Path(__file__).resolve().parent / "browser-final"
OUT.mkdir(exist_ok=True)

SAMPLES = """es => {
  const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently:true});
  const rgba = colour => {
    ctx.clearRect(0,0,1,1); ctx.fillStyle=colour; ctx.fillRect(0,0,1,1);
    return Array.from(ctx.getImageData(0,0,1,1).data);
  };
  const over = (a,b) => a.slice(0,3).map((v,i) => v*a[3]/255+b[i]*(1-a[3]/255));
  return es.filter(e => e.getClientRects().length).map(e => {
    let bg=[255,255,255], ancestors=[], node=e;
    while(node) { ancestors.push(node); node=node.parentElement; }
    ancestors.reverse().forEach(n => { bg=over(rgba(getComputedStyle(n).backgroundColor),bg); });
    const s=getComputedStyle(e);
    return {text:e.textContent.trim().slice(0,100), fg:over(rgba(s.color),bg), bg};
  });
}"""


def luminance(rgb):
    channels = [value / 255 for value in rgb]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
              for value in channels]
    return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))


def ratio(first, second):
    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


report = {"runtime": "legibility-notebook candidate on pipeline-rebuild, baseline6f851d4", "samples": {}, "assets": {}}
with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path="/home/joao/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome",
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    for scheme in ("light", "dark"):
        page.emulate_media(color_scheme=scheme)
        response = page.goto(BASE + "/dados/admin/cms/page/inicio")
        assert response is not None and response.status == 200
        groups = {
            "primary": ".draft-toolbar .btn-primary",
            "danger": ".btn-outline-danger",
            "active_nav": ".nav-link[aria-current='page']",
            "neutral_badges": ".badge.bg-secondary-lt",
            "hints": ".form-hint",
            "sidebar_hint": ".bo-sidebar-foot .quiet",
        }
        for name, selector in groups.items():
            samples = page.locator(selector).evaluate_all(SAMPLES)
            assert samples, (scheme, name, "no actual elements measured")
            for sample in samples:
                sample["ratio"] = ratio(sample["fg"], sample["bg"])
                assert sample["ratio"] >= 4.5, (scheme, name, sample)
            report["samples"][scheme + "/" + name] = samples
        focus = page.locator('input[name="note"]').first
        focus.focus()
        ring = focus.evaluate("""e => {
          const c=document.createElement('canvas').getContext('2d',{willReadFrequently:true});
          const colour=s=>{c.clearRect(0,0,1,1);c.fillStyle=s;c.fillRect(0,0,1,1);return Array.from(c.getImageData(0,0,1,1).data);};
          const s=getComputedStyle(e);
          return {ring:colour(s.outlineColor), surface:colour(s.backgroundColor),
                  outlineStyle:s.outlineStyle, outlineWidth:s.outlineWidth, transition:s.transitionDuration};
        }""")
        ring["composite"] = [v * ring["ring"][3] / 255 + ring["surface"][i] * (1 - ring["ring"][3] / 255)
                             for i, v in enumerate(ring["ring"][:3])]
        ring["ratio"] = ratio(ring["composite"], ring["surface"][:3])
        assert ring["ratio"] >= 3 and ring["outlineStyle"] == "solid" and float(ring["outlineWidth"].removesuffix("px")) >= 2, (scheme, ring)
        report["samples"][scheme + "/focus"] = ring
    page.goto(BASE + "/")
    for name, selector in {"public_primary": ".button", "public_quiet": ".button-quiet", "public_muted": ".lede"}.items():
        samples = page.locator(selector).evaluate_all(SAMPLES)
        assert samples, name
        for sample in samples:
            sample["ratio"] = ratio(sample["fg"], sample["bg"])
            assert sample["ratio"] >= 4.5, (name, sample)
        report["samples"][name] = samples
    for asset in ("static/css/prumo.css", "static/css/admin.css", "static/images/prumo/favicon.svg", "static/js/prumo-charts.min.js", "static/vendor/tabler/1.7.5/tabler.min.css"):
        prefix = "/dados/admin/" if "admin.css" in asset or "vendor/tabler" in asset else "/"
        response = page.request.get(BASE + prefix + asset)
        assert response.status == 200, asset
        fetched = response.body()
        assert fetched == (ROOT / asset).read_bytes(), asset
        report["assets"][asset] = {"bytes": len(fetched), "sha256": hashlib.sha256(fetched).hexdigest()}
    browser.close()
(OUT / "contrast.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps({"groups": len(report["samples"]), "minimum_text_ratio": min(s["ratio"] for g in report["samples"].values() if isinstance(g, list) for s in g), "assets": len(report["assets"])}))
