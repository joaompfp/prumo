"""Typed, bounded documents for the statistics CMS. No I/O and no SQL.

A document body is authored configuration: text, section/block structure and references to
registry series and library charts. It never carries observation values, units or HTML. The
storage layer keeps the canonical JSON produced here, one immutable revision at a time.

Slugs are external keys: lower-kebab-case, at most 60 characters, and never edited in place
(duplicate a document to get a new address).
"""

import html
import json
import re
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Kind = Literal["page", "chart"]
Section = Literal["economy", "demography", "energy", "general"]
# Authored CMS window vocabulary. The built-in series pages keep their existing 10/25/max
# choices; the service layer maps these four values onto the shared chart preparation.
Window = Literal["max", "1y", "5y", "10y"]
Scale = Literal["single", "dual"]

KINDS = ("page", "chart")
MAX_SLUG = 60
MAX_TITLE = 160
MAX_BLOCKS = 12
MAX_TEXT = 4000
MAX_REFERENCE = 200

_SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_REFERENCE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}\Z")
_DAY_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")

# The project forbids U+2014 in authored copy in every spelling. Detection only: the bytes the
# author typed are preserved, or the document is refused. The patterns are assembled so this
# source file itself never contains a forbidden spelling.
_EM_DASH = chr(0x2014)
_BACKSLASH = chr(92)
_EM_DASH_PATTERNS = (
    re.compile(_EM_DASH),
    re.compile(r"&(?:#0*8212|#x0*2014|mdash);?", re.IGNORECASE),
    re.compile("%" + "e2" + "%" + "80" + "%" + "94", re.IGNORECASE),
    re.compile(re.escape(_BACKSLASH) + r"+u(?:0{0,3})?2014", re.IGNORECASE),
    re.compile(re.escape(_BACKSLASH) + r"+u\{0*2014\}", re.IGNORECASE),
    re.compile(re.escape(_BACKSLASH) + r"+U00002014", re.IGNORECASE),
    re.compile(re.escape(_BACKSLASH) + r"+N\{EM DASH\}", re.IGNORECASE),
    re.compile(re.escape(_BACKSLASH) + r"+\{?0*2014\}?(?![0-9A-Fa-f])", re.IGNORECASE),
)


class CmsDocumentError(ValueError):
    """A document outside the typed contract (kind, slug, JSON or canonical form)."""


def validate_kind(kind: str) -> str:
    if kind not in KINDS:
        raise CmsDocumentError(
            f"unknown document kind {kind!r}; expected one of {', '.join(KINDS)}")
    return kind


def validate_slug(slug: str) -> str:
    """Lower-kebab-case external key, 1..60 characters, immutable after creation."""
    if not isinstance(slug, str):
        raise CmsDocumentError("slug must be a string")
    if not 1 <= len(slug) <= MAX_SLUG:
        raise CmsDocumentError(f"slug must be 1..{MAX_SLUG} characters")
    if not _SLUG_RE.fullmatch(slug):
        raise CmsDocumentError(
            f"slug {slug!r} is not lower-kebab-case (letters/digits separated by hyphens)")
    return slug


def _has_em_dash(text: str) -> bool:
    """Detect every spelling without rewriting the authored bytes."""
    if any(pattern.search(text) for pattern in _EM_DASH_PATTERNS):
        return True
    decoded = html.unescape(text)
    return decoded != text and any(
        pattern.search(decoded) for pattern in _EM_DASH_PATTERNS)


def _validate_text(value: str, field: str, *, allow_empty: bool) -> str:
    if not allow_empty and not value.strip():
        raise ValueError(f"{field} must not be empty")
    for char in value:
        if ord(char) < 32 and char not in "\r\n\t":
            raise ValueError(f"{field} contains a control character")
    if _has_em_dash(value):
        raise ValueError(
            f"{field} must not contain a literal or encoded em dash; use an ASCII hyphen")
    return value


def _validate_reference(value: str, field: str) -> str:
    if len(value) > MAX_REFERENCE or not _REFERENCE_RE.fullmatch(value):
        raise ValueError(f"{field} must be a registry reference, not free text")
    return value


class _CmsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TextBlock(_CmsModel):
    type: Literal["text"]
    text: str = Field(min_length=1, max_length=MAX_TEXT)

    @field_validator("text")
    @classmethod
    def _text(cls, value: str) -> str:
        return _validate_text(value, "text", allow_empty=False)


class CardBlock(_CmsModel):
    type: Literal["card"]
    series_id: str = Field(min_length=1, max_length=MAX_REFERENCE)
    derived_key: str | None = Field(default=None, max_length=MAX_REFERENCE)

    @field_validator("series_id")
    @classmethod
    def _series(cls, value: str) -> str:
        return _validate_reference(value, "series_id")

    @field_validator("derived_key")
    @classmethod
    def _derived(cls, value: str | None) -> str | None:
        return None if value is None else _validate_reference(value, "derived_key")


class ChartBlock(_CmsModel):
    type: Literal["chart"]
    chart_slug: str = Field(min_length=1, max_length=MAX_SLUG)

    @field_validator("chart_slug")
    @classmethod
    def _chart_slug(cls, value: str) -> str:
        return validate_slug(value)


Block = Annotated[TextBlock | CardBlock | ChartBlock, Field(discriminator="type")]


class PageDocument(_CmsModel):
    title: str = Field(min_length=1, max_length=MAX_TITLE)
    introduction: str = Field(default="", max_length=MAX_TEXT)
    section: Section
    blocks: list[Block] = Field(max_length=MAX_BLOCKS)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _validate_text(value, "title", allow_empty=False)

    @field_validator("introduction")
    @classmethod
    def _introduction(cls, value: str) -> str:
        return _validate_text(value, "introduction", allow_empty=True)


class ChartDocument(_CmsModel):
    title: str = Field(min_length=1, max_length=MAX_TITLE)
    note: str = Field(max_length=MAX_TEXT)
    series_a: str = Field(min_length=1, max_length=MAX_REFERENCE)
    series_b: str | None = Field(default=None, max_length=MAX_REFERENCE)
    derived_key: str | None = Field(default=None, max_length=MAX_REFERENCE)
    window: Window
    scale: Scale
    day: str | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _validate_text(value, "title", allow_empty=False)

    @field_validator("note")
    @classmethod
    def _note(cls, value: str) -> str:
        return _validate_text(value, "note", allow_empty=True)

    @field_validator("series_a")
    @classmethod
    def _series_a(cls, value: str) -> str:
        return _validate_reference(value, "series_a")

    @field_validator("series_b")
    @classmethod
    def _series_b(cls, value: str | None) -> str | None:
        return None if value is None else _validate_reference(value, "series_b")

    @field_validator("derived_key")
    @classmethod
    def _derived(cls, value: str | None) -> str | None:
        return None if value is None else _validate_reference(value, "derived_key")

    @field_validator("day")
    @classmethod
    def _day(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _DAY_RE.fullmatch(value):
            raise ValueError("day must be an ISO date (YYYY-MM-DD)")
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError(f"day {value!r} is not a real calendar date") from None
        return value

    @model_validator(mode="after")
    def _coherent(self) -> "ChartDocument":
        if self.series_b is not None and self.series_b == self.series_a:
            raise ValueError("series_b must differ from series_a")
        if self.derived_key is not None and self.series_b is not None:
            raise ValueError("derived_key is only allowed on a single-series chart")
        if self.series_b is None and self.scale != "single":
            raise ValueError("a single-series chart uses the single scale")
        return self


Document = PageDocument | ChartDocument


def _reject_constant(value: str) -> None:
    raise CmsDocumentError(f"non-finite JSON constant {value!r} is not allowed")


def _loads(body_json: str) -> object:
    try:
        return json.loads(body_json, parse_constant=_reject_constant)
    except (TypeError, ValueError) as exc:
        raise CmsDocumentError(f"invalid JSON: {exc}") from None


def parse_body(kind: str, body_json: str | bytes | dict) -> Document:
    """Parse one body for `kind` into its typed document, refusing unknown fields."""
    kind = validate_kind(kind)
    if isinstance(body_json, (bytes, bytearray)):
        try:
            body_json = bytes(body_json).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CmsDocumentError(f"document body is not UTF-8: {exc}") from None
    if isinstance(body_json, str):
        data = _loads(body_json)
    elif isinstance(body_json, dict):
        data = body_json
    else:
        raise CmsDocumentError("document body must be JSON text or an object")
    if not isinstance(data, dict):
        raise CmsDocumentError("document body must be a JSON object")
    if kind == "page":
        return PageDocument.model_validate(data)
    return ChartDocument.model_validate(data)


def canonical_body(document: Document) -> str:
    """Stable JSON text: sorted keys, compact separators, Unicode kept as authored."""
    if not isinstance(document, (PageDocument, ChartDocument)):
        raise CmsDocumentError("canonical_body needs a typed PageDocument or ChartDocument")
    return json.dumps(
        document.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_for(kind: str, body_json: str | bytes | dict) -> str:
    """Validate an untrusted body for `kind` and return its canonical text."""
    return canonical_body(parse_body(kind, body_json))


def require_canonical_body(kind: str, body_json: str) -> str:
    """The storage gate: only exactly canonical, kind-valid body text is accepted."""
    if not isinstance(body_json, str):
        raise CmsDocumentError("stored body_json must be canonical JSON text")
    document = parse_body(kind, body_json)
    canonical = canonical_body(document)
    if canonical != body_json:
        raise CmsDocumentError(
            "body_json is not canonical; use canonical_for(kind, body) before storing")
    return canonical
