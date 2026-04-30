"""
London trip endpoints — add/list/delete places from the Obsidian vault.
Used by the joao.date/londres map to create notes remotely (any device).
"""
import os
import re
import yaml
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

router = APIRouter(prefix="/api/london")

VAULT_DIR = "/home/joao/vaults/pessoal/viagens/Londres Abril 2026/Lugares"
CATEGORY_LABELS = {
    "casa": "Base", "cultura": "Cultura", "musica": "Música",
    "parque": "Parques", "gastronomia": "Gastronomia",
    "transporte": "Transporte", "ines": "Roteiro Inês",
}


class PlaceIn(BaseModel):
    name: str
    lat: float
    lng: float
    address: str = ""
    category: str = "cultura"
    desc: str = ""


def safe_filename(name: str) -> str:
    """Convert place name to safe filename."""
    safe = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    return safe[:80] if safe else "Novo Local"


@router.post("/add-place")
def add_place(place: PlaceIn):
    """Create a new Obsidian note for a place. Called from the map."""
    safe = safe_filename(place.name)
    fp = os.path.join(VAULT_DIR, f"{safe}.md")

    if os.path.exists(fp):
        return JSONResponse(status_code=409, content={
            "error": "already_exists",
            "message": f"Nota '{safe}' já existe.",
            "file": f"{safe}.md"
        })

    content = "\n".join([
        "---",
        f"tags: [viagem/london-2026, lugar]",
        f"trip: Londres Abril 2026",
        f"location: [{place.lat:.6f}, {place.lng:.6f}]",
        f'address: "{place.address}"',
        f"category: {place.category}",
        f"added: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "---",
        "",
        f"# {place.name}",
        "",
        place.desc or "Descrição a preencher.",
        "",
    ])

    os.makedirs(VAULT_DIR, exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)

    return {"ok": True, "file": f"{safe}.md", "name": place.name}


@router.get("/places")
def list_places():
    """Return all places from the vault as JSON."""
    places = []
    if not os.path.isdir(VAULT_DIR):
        return places
    for fn in sorted(os.listdir(VAULT_DIR)):
        if not fn.endswith(".md"):
            continue
        fp = os.path.join(VAULT_DIR, fn)
        try:
            with open(fp, encoding="utf-8") as f:
                content = f.read()
            m = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
            if not m:
                continue
            meta = yaml.safe_load(m.group(1))
            body = m.group(2).strip()
            if not meta.get("location"):
                continue
            loc = meta["location"]
            lines = [l.strip() for l in body.split('\n')
                     if l.strip() and not l.startswith('#') and not l.startswith('📍')]
            desc = lines[0] if lines else ""
            desc = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', desc)
            desc = re.sub(r'[*_`#>]', '', desc).strip()
            cat = meta.get("category", "cultura")
            places.append({
                "name": os.path.splitext(fn)[0],
                "lat": loc[0], "lng": loc[1],
                "address": meta.get("address", ""),
                "category": cat,
                "label": CATEGORY_LABELS.get(cat, cat),
                "desc": desc,
            })
        except Exception:
            continue
    return places


@router.delete("/place/{name}")
def delete_place(name: str):
    """Delete a place note."""
    safe = safe_filename(name)
    fp = os.path.join(VAULT_DIR, f"{safe}.md")
    if not os.path.exists(fp):
        return JSONResponse(status_code=404, content={"error": "not_found"})
    os.remove(fp)
    return {"ok": True, "deleted": f"{safe}.md"}
