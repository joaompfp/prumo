"""Choose the public homepage from one read-only snapshot.

Before the first CMS publication, `/` remains the existing home, including its editorial
composition. Afterwards the CMS document owns `/`: drafts are private, an unpublish is a
neutral page with the site navigation, and a published revision that cannot be parsed fails
closed instead of falling back to the old list.
"""
from dataclasses import dataclass

from app import cms_reads, reads
from ingest.db import Db


@dataclass(frozen=True)
class HomeRender:
    template: str
    context: dict
    status: int = 200
    script: bool = False


NEUTRAL_TEMPLATE = "home_unpublished.html"
UNAVAILABLE_TEMPLATE = "home_unavailable.html"


def page(db: Db, lang: str = "pt") -> HomeRender:
    """The template, context and script decision for `/`; never mutates or publishes."""
    state = cms_reads.home_state(db, lang)
    if state.mode == "legacy":
        return HomeRender("home.html", {"page": reads.home(db, lang)})
    if state.mode == "published":
        assert state.page is not None
        return HomeRender("cms_home.html", {"page": state.page},
                          script=state.page.chart_payload is not None)
    if state.mode == "unpublished":
        return HomeRender(NEUTRAL_TEMPLATE, {})
    return HomeRender(UNAVAILABLE_TEMPLATE, {}, status=503)
