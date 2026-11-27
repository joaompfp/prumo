"""Read back the exact public CMS targets after the scope-only correction."""
import concurrent.futures
import importlib.util
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
plan = json.loads((ROOT / "docs/editorial/2026-11-27-existing-sections-correction/plan.json").read_text())
spec = importlib.util.spec_from_file_location("collection_qa", Path(__file__).parents[1] / "national-debate/acceptance.py")
assert spec is not None and spec.loader is not None
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Prumo-editorial-scope-readback/1"})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


checks = []


def check(name, value):
    checks.append({"name": name, "passed": bool(value)})
    assert value, name


completed = False
try:
    for origin, prefix in (("https://joao.date/dados", "/dados"), ("https://cae.joao.date", "")):
        paths = ["/", "/paginas", "/comparar", "/temas/economy", "/temas/demography", "/temas/energy"]
        paths += ["/paginas/" + item["slug"] for item in plan["updates"] + plan["retire"]]
        paths += ["/comparar/" + slug for slug in plan["preserve_charts"]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = dict(zip(paths, pool.map(fetch, [origin + path for path in paths])))
        for path, (status, text) in results.items():
            retired = path in {"/paginas/" + item["slug"] for item in plan["retire"]}
            check(origin + path + ": correct public status", status == (404 if retired else 200))
            if not retired:
                check(origin + path + ": no unwanted label or orphan reference", "debate nacional" not in text.lower() and all("/paginas/" + item["slug"] not in text for item in plan["retire"]))
        for item in plan["updates"]:
            slug = item["slug"]
            text = results["/paginas/" + slug][1]
            check(origin + ": thematic page exact title " + slug, qa.PageParser(text).headings == [item["after"]["title"]])
            link = prefix + "/paginas/" + slug
            check(origin + ": discoverable through existing pages and theme " + slug, link in results["/paginas"][1] and link in results["/temas/" + item["after"]["section"]][1])
        for slug in plan["preserve_charts"]:
            check(origin + ": comparison remains in normal library " + slug, prefix + "/comparar/" + slug in results["/comparar"][1])
            parsed = qa.PageParser(results["/comparar/" + slug][1])
            check(origin + ": comparison remains fully populated " + slug, len(parsed.payloads) == 1 and len(parsed.payloads[0]["series"]) >= 2 and len(parsed.payloads[0]["x"]) > 1)
    completed = True
finally:
    receipt = {"completed": completed, "passed": completed and all(item["passed"] for item in checks), "checks": checks}
    target = Path(__file__).with_name("public.json")
    target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"completed": completed, "checks": len(checks), "receipt": str(target)}))
