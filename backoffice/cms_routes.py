"""Statistics CMS in the backoffice: labelled forms, lifecycle and the authenticated preview.

This module owns the editor surface only. The typed document contracts live in `ingest.cms`,
the lifecycle and eligibility rules in `backoffice.cms`, and the public rendering in the
public app's own templates. Here we turn ordinary form fields into the document dict shape,
map service refusals onto status codes, and keep every write behind the admin origin check
and the authenticated actor.

A form uses one unique field name per block index (`block_text_0`, `block_series_0`, ...),
because `AdminContext.form` flattens repeated names. The reader below is stricter: it bounds
the body, rejects duplicate names, accepts only the exact keys this editor renders inside
the block limit, and ignores unknown keys (submit buttons carry their action in their name).
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from backoffice.access import ADMIN_PREFIX
from backoffice.cms import (
    HOME_SLUG,
    Cms,
    CmsBusy,
    CmsConflict,
    CmsNotFound,
    CmsRefused,
    CmsUnavailable,
)
from backoffice.deps import LANG
from backoffice.forms import parse_int
from ingest.cms import KINDS, MAX_BLOCKS, MAX_SLUG, MAX_TEXT, MAX_TITLE

PAGE_METHODS = ["GET", "HEAD"]
# The preview links the real public stylesheet from this app's /static mount. Everything else
# keeps the backoffice policy from `backoffice.app`; neither policy permits a script.
PREVIEW_CSP = ("default-src 'none'; style-src 'self' 'unsafe-inline'; "
               "img-src 'self' data:; form-action 'self'; base-uri 'none'; "
               "frame-ancestors 'none'")
# The editor form is bigger than the editorial one (12 blocks), but still explicitly bounded.
CMS_FORM_MAX_BYTES = 131_072
MAX_FIELDS = 200  # 12 block rows x 5 fields + controls + the scalar fields, with headroom

_SCALARS = frozenset({
    "title", "introduction", "section", "note", "note_text", "version", "block_count",
    "op", "kind", "slug", "new_slug", "revision_id", "series_a", "series_b",
    "derived_key", "window", "scale", "day",
    "add_type", "add_text", "add_series", "add_derived", "add_chart",
})
_BLOCK = re.compile(r"block_(type|text|series|derived|chart)_([0-9]{1,2})\Z")
_CONTROL = re.compile(r"(move_up|move_down|remove)_([0-9]{1,2})\Z")
_SECTIONS = ("economy", "demography", "energy", "general")
_WINDOWS = ("max", "1y", "5y", "10y")
_SCALES = ("single", "dual")


class FormError(ValueError):
    """A form the editor refuses before it reaches the service."""


async def _read_form(request: Request) -> tuple[dict[str, str], dict[str, str]]:
    """Read the bounded form. Returns (values, pressed block controls)."""
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > CMS_FORM_MAX_BYTES:
        raise HTTPException(status_code=413, detail="form too large")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > CMS_FORM_MAX_BYTES:
            raise HTTPException(status_code=413, detail="form too large")
        body.extend(chunk)
    try:
        text = bytes(body).decode("utf-8")
    except UnicodeDecodeError:
        raise FormError("o formulário não está em UTF-8") from None
    try:
        parsed = parse_qs(text, keep_blank_values=True, max_num_fields=MAX_FIELDS)
    except ValueError as exc:
        raise FormError(f"formulário inválido: {exc}") from None
    values: dict[str, str] = {}
    controls: dict[str, str] = {}
    for name, items in parsed.items():
        if len(items) != 1:
            raise FormError(f"campo repetido no formulário: {name}")
        value = items[0]
        if name in _SCALARS:
            values[name] = value
            continue
        block = _BLOCK.fullmatch(name)
        if block is not None:
            if int(block.group(2)) >= MAX_BLOCKS:
                raise FormError(f"índice de bloco fora do limite: {name}")
            values[name] = value
            continue
        control = _CONTROL.fullmatch(name)
        if control is not None:
            if int(control.group(2)) >= MAX_BLOCKS:
                raise FormError(f"índice de bloco fora do limite: {name}")
            controls[name] = value
            continue
        # Unknown keys are ignored on purpose: a submit button may carry an action value.
    return values, controls


def _version(fields: dict[str, str]) -> int:
    try:
        return parse_int(fields.get("version", ""), field="versão")
    except ValueError:
        raise FormError("versão em falta ou inválida; recarregue o editor") from None


def _note(fields: dict[str, str]) -> str:
    note = fields.get("note", "")
    if not note.strip():
        raise FormError("o motivo é obrigatório")
    if len(note) > MAX_TEXT:
        raise FormError(f"o motivo não pode exceder {MAX_TEXT} caracteres")
    return note


def _block_count(fields: dict[str, str]) -> int:
    try:
        count = parse_int(fields.get("block_count", "0") or "0", field="número de blocos")
    except ValueError:
        raise FormError(f"o número de blocos tem de estar entre 0 e {MAX_BLOCKS}") from None
    if count > MAX_BLOCKS:
        raise FormError(f"o número de blocos tem de estar entre 0 e {MAX_BLOCKS}")
    return count


def _page_body(fields: dict[str, str]) -> dict:
    blocks = []
    for index in range(_block_count(fields)):
        kind = fields.get(f"block_type_{index}", "").strip()
        if kind == "text":
            blocks.append({"type": "text", "text": fields.get(f"block_text_{index}", "")})
        elif kind == "card":
            blocks.append({
                "type": "card",
                "series_id": fields.get(f"block_series_{index}", ""),
                "derived_key": fields.get(f"block_derived_{index}", "").strip() or None,
            })
        elif kind == "chart":
            blocks.append({
                "type": "chart",
                "chart_slug": fields.get(f"block_chart_{index}", ""),
            })
        else:
            raise FormError(f"bloco {index + 1}: tipo de bloco desconhecido")
    return {
        "title": fields.get("title", ""),
        "introduction": fields.get("introduction", ""),
        "section": fields.get("section", ""),
        "blocks": blocks,
    }


def _chart_body(fields: dict[str, str]) -> dict:
    return {
        "title": fields.get("title", ""),
        "note": fields.get("note_text", ""),
        "series_a": fields.get("series_a", ""),
        "series_b": fields.get("series_b", "").strip() or None,
        "derived_key": fields.get("derived_key", "").strip() or None,
        "window": fields.get("window", ""),
        "scale": fields.get("scale", ""),
        "day": fields.get("day", "").strip() or None,
    }


def _add_block(fields: dict[str, str]) -> dict:
    kind = fields.get("add_type", "").strip()
    if kind == "text":
        return {"type": "text", "text": fields.get("add_text", "")}
    if kind == "card":
        return {
            "type": "card",
            "series_id": fields.get("add_series", ""),
            "derived_key": fields.get("add_derived", "").strip() or None,
        }
    if kind == "chart":
        return {"type": "chart", "chart_slug": fields.get("add_chart", "")}
    raise FormError("escolha o tipo de bloco a acrescentar")


def _apply_block_control(body: dict, controls: dict[str, str]) -> dict:
    """Move or remove one rendered block; the whole document is saved afterwards."""
    if len(controls) != 1:
        raise FormError("o formulário traz mais de uma ação de bloco")
    blocks = body["blocks"]
    name, _ = next(iter(controls.items()))
    match = _CONTROL.fullmatch(name)
    assert match is not None  # _read_form only admits this shape
    action, index = match.group(1), int(match.group(2))
    if index >= len(blocks):
        raise FormError(f"bloco {index + 1}: não existe no formulário")
    if action == "remove":
        del blocks[index]
    elif action == "move_up" and index > 0:
        blocks[index - 1], blocks[index] = blocks[index], blocks[index - 1]
    elif action == "move_down" and index < len(blocks) - 1:
        blocks[index], blocks[index + 1] = blocks[index + 1], blocks[index]
    return body


def _document_from_fields(kind: str, fields: dict[str, str],
                          controls: dict[str, str]) -> dict:
    if kind == "chart":
        if controls or fields.get("op", "save") != "save":
            raise FormError("um gráfico não tem blocos")
        return _chart_body(fields)
    body = _page_body(fields)
    if controls:
        return _apply_block_control(body, controls)
    op = fields.get("op", "save")
    if op == "save":
        return body
    if op == "add":
        if len(body["blocks"]) >= MAX_BLOCKS:
            raise FormError(f"uma página tem no máximo {MAX_BLOCKS} blocos")
        body["blocks"].append(_add_block(fields))
        return body
    raise FormError(f"ação de editor desconhecida: {op}")


def _short(value) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    return text if len(text) <= 120 else text[:117] + "..."


def _page_label(block: dict) -> str:
    kind = block.get("type")
    if kind == "text":
        return f"texto: {_short(block.get('text'))}"
    if kind == "card":
        suffix = f" + {block.get('derived_key')}" if block.get("derived_key") else ""
        return f"cartão: {block.get('series_id')}{suffix}"
    if kind == "chart":
        return f"gráfico: {block.get('chart_slug')}"
    return "bloco desconhecido"


def _diff(kind: str, live: dict | None, draft: dict | None) -> list[dict[str, str]]:
    """The fields that publishing would change, in the operator's words."""
    if live is None or not isinstance(draft, dict):
        return []
    rows: list[dict[str, str]] = []
    fields = (("Título", "title"), ("Introdução", "introduction"), ("Secção", "section")) \
        if kind == "page" else (
            ("Título", "title"), ("Nota", "note"), ("Série A", "series_a"),
            ("Série B", "series_b"), ("Série calculada", "derived_key"),
            ("Janela", "window"), ("Escala", "scale"), ("Dia UTC", "day"))
    for label, key in fields:
        before, after = live.get(key), draft.get(key)
        if before != after:
            rows.append({"field": label, "live": _short(before) or "(vazio)",
                         "draft": _short(after) or "(vazio)"})
    if kind == "page":
        old, new = live.get("blocks") or [], draft.get("blocks") or []
        if len(old) != len(new):
            rows.append({"field": "Blocos", "live": str(len(old)), "draft": str(len(new))})
        for index in range(min(len(old), len(new))):
            # Detect the change on the whole block: the 120-character label is display only,
            # so two long texts that differ after that point are still a reported change.
            if old[index] != new[index]:
                rows.append({"field": f"Bloco {index + 1}",
                             "live": _page_label(old[index]),
                             "draft": _page_label(new[index])})
    return rows


def _metadata(meta: dict) -> dict:
    """Template-facing head metadata, with the published time resolved from history."""
    return {
        "kind": meta["kind"],
        "slug": meta["slug"],
        "version": meta["version"],
        "draft_revision_id": meta.get("draft_revision_id"),
        "published_revision_id": meta.get("published_revision_id"),
        "created_at": meta.get("created_at"),
        "updated_at": meta.get("updated_at"),
    }


_PUBLIC_PREFIX = re.compile(r"/(?:[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*)?")


def _public_base(asset_base: str) -> str:
    """The public mount for data links in a preview, or '' when there is no configured one.

    Under the deployed Admin mount the public app is the same origin without the `/admin`
    suffix. Direct development has no shared prefix, so an explicit `PRUMO_PUBLIC_BASE`
    (for example `http://localhost:8000`) is used; an invalid value is ignored, never echoed.
    """
    if asset_base == ADMIN_PREFIX:
        return ADMIN_PREFIX.removesuffix("/admin")
    configured = os.environ.get("PRUMO_PUBLIC_BASE", "").strip().rstrip("/")
    if configured and (configured.startswith("http://") or configured.startswith("https://")):
        return configured
    return configured if _PUBLIC_PREFIX.fullmatch(configured) else ""


def register_cms(app: FastAPI, admin, db_path: Path, editorial_db_path: Path | None) -> None:
    """Mount the CMS editor on an existing backoffice app. No second auth or prefix logic."""
    from app.main import NAV
    from app.main import _templates as public_templates

    cms = Cms(Path(db_path), editorial_db_path, lang=LANG)
    app.state.cms = cms
    preview_templates = public_templates()

    def render_error(request: Request, status: int, title: str, message: str):
        return admin.render(request, "error.html", status, title=title, message=message)

    def editor_page(request: Request, kind: str, slug: str, *, status_code: int = 200,
                    error: str | None = None, doc: dict | None = None):
        if kind not in KINDS:
            return render_error(request, 404, "Documento desconhecido",
                                f"tipo de documento desconhecido: {kind}")
        try:
            data = cms.get(kind, slug)
        except CmsNotFound:
            data = None
        except CmsRefused:
            data = None
        except (CmsUnavailable, CmsBusy) as exc:
            return render_error(request, 503, "Editor CMS indisponível", str(exc))
        if data is None:
            return render_error(request, 404, "Documento desconhecido",
                                f"{kind}/{slug} não existe")
        meta = _metadata(data["meta"])
        published = data["published"].model_dump(mode="json") if data["published"] else None
        draft = data.get("draft")
        if draft is None:
            return render_error(request, 503, "Documento indisponível",
                                f"{kind}/{slug}: o corpo do rascunho não pôde ser lido")
        if doc is None:
            doc = draft.model_dump(mode="json")
        history = data.get("history", ())
        published_at = None
        if meta["published_revision_id"] is not None:
            for revision in history:
                if revision["id"] == meta["published_revision_id"]:
                    published_at = revision["created_at"]
                    break
        try:
            choices = cms.choices()
            charts = cms.charts() if kind == "page" else ()
        except (CmsUnavailable, CmsBusy) as exc:
            return render_error(request, 503, "Editor CMS indisponível", str(exc))
        return admin.render(
            request, "cms_editor.html", status_code=status_code, kind=kind, slug=slug,
            meta=meta, doc=doc, published=published, published_at=published_at,
            diff=_diff(kind, published, doc), history=history,
            events=data.get("events", ()), usages=data.get("usages", ()),
            choices=choices, charts=charts, sections=_SECTIONS, windows=_WINDOWS,
            scales=_SCALES, max_blocks=MAX_BLOCKS, max_slug=MAX_SLUG,
            max_title=MAX_TITLE, max_text=MAX_TEXT, error=error,
            is_home=(kind == "page" and slug == HOME_SLUG))

    def list_page(request: Request, *, status_code: int = 200, error: str | None = None,
                  values: dict[str, str] | None = None):
        try:
            pages = cms.list("page")
            charts = cms.list("chart")
            choices = cms.choices()
            home = cms.home()
        except (CmsUnavailable, CmsBusy) as exc:
            return render_error(request, 503, "Editor CMS indisponível", str(exc))
        return admin.render(
            request, "cms_list.html", status_code=status_code, pages=pages, charts=charts,
            choices=choices, values=values or {}, home=home,
            sections=_SECTIONS, windows=_WINDOWS, scales=_SCALES,
            max_blocks=MAX_BLOCKS, max_slug=MAX_SLUG, max_title=MAX_TITLE, max_text=MAX_TEXT,
            error=error)

    @app.api_route("/cms", methods=PAGE_METHODS)
    def cms_dashboard(request: Request):
        return list_page(request)

    def home_page(request: Request, *, status_code: int = 200, error: str | None = None):
        try:
            home = cms.home()
        except (CmsUnavailable, CmsBusy) as exc:
            return render_error(request, 503, "Editor CMS indisponível", str(exc))
        if home is not None and status_code == 200:
            return RedirectResponse(admin.url(request, f"/cms/page/{HOME_SLUG}"),
                                    status_code=302)
        return admin.render(request, "cms_home.html", status_code=status_code, home=home,
                            available=cms.available(), error=error)

    @app.api_route("/cms/home", methods=PAGE_METHODS)
    def cms_home(request: Request):
        return home_page(request)

    @app.post("/cms/home/prepare")
    async def cms_home_prepare(request: Request):
        """Explicit, same-origin, audited creation of the private home draft."""
        admin.guard(request)
        fields: dict[str, str] = {}
        try:
            fields, _ = await _read_form(request)
            note = _note(fields)
        except FormError as exc:
            return await run_in_threadpool(home_page, request, status_code=422,
                                           error=str(exc))
        except HTTPException:
            raise
        try:
            await run_in_threadpool(cms.prepare_home, actor=admin.actor(request), note=note)
        except CmsConflict as exc:
            return await run_in_threadpool(editor_page, request, "page", HOME_SLUG,
                                           status_code=409, error=str(exc))
        except CmsRefused as exc:
            return await run_in_threadpool(home_page, request, status_code=422, error=str(exc))
        except (CmsUnavailable, CmsBusy) as exc:
            status = 503
            title = ("Editor ocupado" if isinstance(exc, CmsBusy)
                     else "Editor CMS indisponível")
            return render_error(request, status, title, str(exc))
        return RedirectResponse(admin.url(request, f"/cms/page/{HOME_SLUG}"), status_code=303)

    @app.api_route("/cms/{kind}/{slug}/preview", methods=PAGE_METHODS)
    def cms_preview(request: Request, kind: str, slug: str):
        if kind not in KINDS:
            return render_error(request, 404, "Documento desconhecido",
                                f"tipo de documento desconhecido: {kind}")
        try:
            prepared = cms.preview(kind, slug)
        except (CmsNotFound, CmsRefused):
            prepared = None
        except (CmsUnavailable, CmsBusy) as exc:
            return render_error(request, 503, "Pré-visualização indisponível", str(exc))
        if prepared is None:
            return render_error(request, 404, "Documento desconhecido",
                                f"{kind}/{slug} não existe")
        template_name, view = prepared
        # The service may hand back a ready context dict or the prepared view itself. The
        # public templates read `page` for a page and `chart` for a chart; supplying both names
        # keeps the preview exact without a second rendering path. Admin values come last so a
        # prepared mapping cannot rewrite the mount prefix or turn the script back on.
        context = dict(view) if isinstance(view, Mapping) else {"page": view, "chart": view}
        asset_base = admin.base(request)
        context.update(base=_public_base(asset_base), asset_base=asset_base, nav=NAV,
                       path=request.url.path,
                       admin_base=admin.url(request, f"/cms/{kind}/{slug}"), preview=True)
        response = preview_templates.TemplateResponse(request, template_name, context)
        response.headers["Content-Security-Policy"] = PREVIEW_CSP
        return response

    @app.api_route("/cms/{kind}/{slug}", methods=PAGE_METHODS)
    def cms_editor(request: Request, kind: str, slug: str):
        return editor_page(request, kind, slug)

    @app.post("/cms/new")
    async def cms_new(request: Request):
        admin.guard(request)
        fields: dict[str, str] = {}
        try:
            fields, _ = await _read_form(request)
            kind = fields.get("kind", "")
            if kind not in KINDS:
                return render_error(request, 404, "Documento desconhecido",
                                    f"tipo de documento desconhecido: {kind}")
            slug = fields.get("slug", "")
            note = _note(fields)
            body = _chart_body(fields) if kind == "chart" else {
                "title": fields.get("title", ""),
                "introduction": fields.get("introduction", ""),
                "section": fields.get("section", ""),
                "blocks": [],
            }
        except FormError as exc:
            return await run_in_threadpool(list_page, request, status_code=422,
                                           error=str(exc), values=fields)
        except HTTPException:
            raise
        try:
            created = await run_in_threadpool(
                cms.create, kind, slug, body, actor=admin.actor(request), note=note)
        except CmsConflict as exc:
            return await run_in_threadpool(editor_page, request, kind, slug,
                                           status_code=409, error=str(exc))
        except CmsRefused as exc:
            return await run_in_threadpool(list_page, request, status_code=422,
                                           error=str(exc), values=fields)
        except CmsNotFound:
            return render_error(request, 404, "Documento desconhecido", f"{kind}/{slug}")
        except (CmsUnavailable, CmsBusy) as exc:
            return render_error(request, 503, "Editor CMS indisponível", str(exc))
        return RedirectResponse(admin.url(request, f"/cms/{kind}/{created['slug']}"),
                                status_code=303)

    async def mutate(request: Request, kind: str, slug: str, action: str):
        admin.guard(request)
        if kind not in KINDS:
            return render_error(request, 404, "Documento desconhecido",
                                f"tipo de documento desconhecido: {kind}")
        doc = None
        try:
            fields, controls = await _read_form(request)
            version = _version(fields)
            note = _note(fields)
            doc = (_document_from_fields(kind, fields, controls)
                   if action == "save" else None)
        except FormError as exc:
            return await run_in_threadpool(editor_page, request, kind, slug,
                                           status_code=422, error=str(exc), doc=doc)
        except HTTPException:
            raise
        try:
            result = None
            if action == "save":
                await run_in_threadpool(cms.save, kind, slug, version, doc,
                                        actor=admin.actor(request), note=note)
            elif action == "publish":
                await run_in_threadpool(cms.publish, kind, slug, version,
                                        actor=admin.actor(request), note=note)
            elif action == "unpublish":
                await run_in_threadpool(cms.unpublish, kind, slug, version,
                                        actor=admin.actor(request), note=note)
            elif action == "restore":
                try:
                    revision = parse_int(fields.get("revision_id", ""), field="revisão")
                except ValueError:
                    raise FormError("revisão em falta ou inválida") from None
                await run_in_threadpool(cms.restore, kind, slug, version, revision,
                                        actor=admin.actor(request), note=note)
            elif action == "duplicate":
                result = await run_in_threadpool(cms.duplicate, kind, slug,
                                                 fields.get("new_slug", ""), version=version,
                                                 actor=admin.actor(request), note=note)
            else:  # pragma: no cover - each route below names its action
                raise FormError(f"ação desconhecida: {action}")
        except FormError as exc:
            return await run_in_threadpool(editor_page, request, kind, slug,
                                           status_code=422, error=str(exc), doc=doc)
        except CmsConflict as exc:
            return await run_in_threadpool(editor_page, request, kind, slug,
                                           status_code=409, error=str(exc), doc=doc)
        except CmsRefused as exc:
            return await run_in_threadpool(editor_page, request, kind, slug,
                                           status_code=422, error=str(exc), doc=doc)
        except CmsNotFound:
            return render_error(request, 404, "Documento desconhecido",
                                f"{kind}/{slug} não existe")
        except (CmsUnavailable, CmsBusy) as exc:
            status = 503
            title = ("Editor ocupado" if isinstance(exc, CmsBusy)
                     else "Editor CMS indisponível")
            return render_error(request, status, title, str(exc))
        target = (f"/cms/{kind}/{result['slug'] if result else slug}"
                  if action == "duplicate" else f"/cms/{kind}/{slug}")
        return RedirectResponse(admin.url(request, target), status_code=303)

    @app.post("/cms/{kind}/{slug}/save")
    async def cms_save(request: Request, kind: str, slug: str):
        return await mutate(request, kind, slug, "save")

    @app.post("/cms/{kind}/{slug}/publish")
    async def cms_publish(request: Request, kind: str, slug: str):
        return await mutate(request, kind, slug, "publish")

    @app.post("/cms/{kind}/{slug}/unpublish")
    async def cms_unpublish(request: Request, kind: str, slug: str):
        return await mutate(request, kind, slug, "unpublish")

    @app.post("/cms/{kind}/{slug}/restore")
    async def cms_restore(request: Request, kind: str, slug: str):
        return await mutate(request, kind, slug, "restore")

    @app.post("/cms/{kind}/{slug}/duplicate")
    async def cms_duplicate(request: Request, kind: str, slug: str):
        return await mutate(request, kind, slug, "duplicate")
