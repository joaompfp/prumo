"""Populate deterministic comparison fixtures through the real CMS publication service."""
from backoffice.cms import Cms
from backoffice.comparison_import import definitions, install


def publish_comparisons(path, slugs):
    selected = set(slugs)
    entries = tuple(entry for entry in definitions() if entry.slug in selected)
    assert {entry.slug for entry in entries} == selected
    return install(Cms(path, path), actor="fixture", note="publish authored fixture", publish=True,
                   entries=entries)
