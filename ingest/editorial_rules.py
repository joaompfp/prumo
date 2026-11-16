"""Which series may occupy a slot on a public page.

One pure rule, called by the backoffice before it publishes and by the site when it renders.
It has no I/O, no database handle, no logging and no reader text, so the two callers cannot
drift into different answers: the publish refusal and the render-time drop are the same
function applied to the same facts.

A slot that stops qualifying at render time must cost one card, never a 503 and never a hole.
That is why the rule returns a short machine reason instead of raising: the caller decides
whether to refuse (write time) or to drop and log (read time).

The title requirement is per LANGUAGE, not "both catalogues". The English catalogue is
deliberately empty in v1, so demanding an English title would make every series ineligible for
a page rendered in Portuguese. A page is checked in the language it will be rendered in, and
when English ships the same rule runs with lang="en" and drops what it cannot name.
"""

from dataclasses import dataclass, field

MAX_SLOTS = 12

# The closed vocabulary of reasons. A test asserts every one of these is reachable.
REASONS = frozenset({
    "unknown_series",
    "inactive",
    "cross_check",
    "withheld",
    "no_served_value",
    "missing_title",
    "duplicate_title",
    "unknown_derived",
    "inactive_derived",
    "derived_base_mismatch",
    "derived_missing_title",
})


@dataclass(frozen=True)
class SlotFacts:
    """Everything the rule needs about one slot, resolved by the caller.

    `titles` holds the title each catalogue would render, per language, or None where the
    catalogue cannot name that family and geography. Titles, not ids, are what collide: the
    seasonal and unadjusted variants of one indicator share both family and geography, so
    they render the same label and would appear as two identical cards.
    """

    series_id: str
    active: bool
    role: str
    redistribution_ok: bool
    has_served: bool
    titles: dict[str, str | None] = field(default_factory=dict)
    derived_key: str | None = None
    derived_active: bool = False
    derived_base_series_id: str | None = None
    derived_titles: dict[str, str | None] = field(default_factory=dict)


def slot_problem(facts: SlotFacts | None, *, titles_taken: set[str], lang: str = "pt") -> str | None:
    """None when the slot may stand, else the first failing reason in a fixed order."""
    if facts is None:
        return "unknown_series"
    if not facts.active:
        return "inactive"
    if facts.role != "primary":
        return "cross_check"
    if not facts.redistribution_ok:
        return "withheld"
    if not facts.has_served:
        return "no_served_value"
    title = facts.titles.get(lang)
    if not title:
        return "missing_title"
    if title in titles_taken:
        return "duplicate_title"
    if facts.derived_key:
        if facts.derived_base_series_id is None:
            return "unknown_derived"
        if not facts.derived_active:
            return "inactive_derived"
        if facts.derived_base_series_id != facts.series_id:
            return "derived_base_mismatch"
        if not facts.derived_titles.get(lang):
            return "derived_missing_title"
    return None


def page_problems(facts: list[SlotFacts | None], *, lang: str = "pt") -> list[tuple[int, str]]:
    """(position, reason) for every failing slot, in page order, in Portuguese.

    Duplicate titles resolve in page order: the first slot keeps the title, later ones fail.
    That is the same order the reader sees, so a publish refusal names the card the operator
    would have seen disappear.
    """
    problems: list[tuple[int, str]] = []
    taken: set[str] = set()
    for position, slot in enumerate(facts):
        problem = slot_problem(slot, titles_taken=taken, lang=lang)
        if problem is not None:
            problems.append((position, problem))
            continue
        title = (slot.titles.get(lang) if slot else None)
        if title:
            taken.add(title)
    return problems
