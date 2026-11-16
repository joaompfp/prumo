"""The eligibility rule: one function, every reason reachable, duplicates in page order."""

import pytest

from ingest.editorial_rules import REASONS, SlotFacts, page_problems, slot_problem


def facts(**overrides):
    base = dict(
        series_id="ine.hicp_yoy.PT",
        active=True,
        role="primary",
        redistribution_ok=True,
        has_served=True,
        title_pt="Inflação (IHPC)",
        title_en="Inflation (HICP)",
    )
    return SlotFacts(**(base | overrides))


def reason_for(**overrides):
    return slot_problem(facts(**overrides), titles_taken=set())


def test_a_plain_primary_series_is_eligible():
    assert reason_for() is None


@pytest.mark.parametrize("overrides, expected", [
    ({"active": False}, "inactive"),
    ({"role": "cross_check"}, "cross_check"),
    ({"redistribution_ok": False}, "withheld"),
    ({"has_served": False}, "no_served_value"),
    ({"title_pt": None}, "missing_title_pt"),
    ({"title_en": None}, "missing_title_en"),
    ({"derived_key": "derived.x.yoy_change", "derived_base_series_id": None}, "unknown_derived"),
    ({"derived_key": "derived.x.yoy_change", "derived_base_series_id": "ine.hicp_yoy.PT",
      "derived_active": False}, "inactive_derived"),
    ({"derived_key": "derived.x.yoy_change", "derived_base_series_id": "ine.other.PT",
      "derived_active": True, "derived_title_pt": "Variação", "derived_title_en": "Change"},
     "derived_base_mismatch"),
    ({"derived_key": "derived.x.yoy_change", "derived_base_series_id": "ine.hicp_yoy.PT",
      "derived_active": True, "derived_title_pt": "Variação", "derived_title_en": None},
     "derived_missing_title"),
])
def test_each_failure_reason(overrides, expected):
    assert reason_for(**overrides) == expected


def test_every_declared_reason_is_reachable():
    """The vocabulary is closed: a reason with no test is a reason nobody has thought about."""
    exercised = set()
    for overrides, expected in [
        ({"active": False}, "inactive"),
        ({"role": "cross_check"}, "cross_check"),
        ({"redistribution_ok": False}, "withheld"),
        ({"has_served": False}, "no_served_value"),
        ({"title_pt": None}, "missing_title_pt"),
        ({"title_en": None}, "missing_title_en"),
        ({"derived_key": "d", "derived_base_series_id": None}, "unknown_derived"),
        ({"derived_key": "d", "derived_base_series_id": "ine.hicp_yoy.PT",
          "derived_active": False}, "inactive_derived"),
        ({"derived_key": "d", "derived_base_series_id": "ine.other.PT",
          "derived_active": True, "derived_title_pt": "x", "derived_title_en": "x"},
         "derived_base_mismatch"),
        ({"derived_key": "d", "derived_base_series_id": "ine.hicp_yoy.PT",
          "derived_active": True, "derived_title_pt": "x"}, "derived_missing_title"),
    ]:
        exercised.add(reason_for(**overrides))
    exercised.add(slot_problem(None, titles_taken=set()))
    exercised.add(slot_problem(facts(), titles_taken={"Inflação (IHPC)"}))
    assert exercised == set(REASONS)


def test_a_valid_derived_companion_is_eligible():
    f = facts(derived_key="derived.hicp_yoy.PT.yoy_change",
              derived_base_series_id="ine.hicp_yoy.PT", derived_active=True,
              derived_title_pt="Inflação, variação homóloga (%)",
              derived_title_en="Inflation, year-on-year change (%)")
    assert slot_problem(f, titles_taken=set()) is None


def test_duplicate_title_is_the_same_label_not_the_same_id():
    seasonal = facts(series_id="ine.ipi_seasonal.PT")
    unadjusted = facts(series_id="ine.ipi.PT")
    problems = page_problems([seasonal, unadjusted])
    assert problems == [(1, "duplicate_title")]


def test_duplicate_keeps_the_first_position():
    a = facts(series_id="ine.a.PT", title_pt="Produção industrial")
    b = facts(series_id="ine.b.PT", title_pt="Produção industrial")
    c = facts(series_id="ine.c.PT", title_pt="Desemprego")
    assert page_problems([a, b, c]) == [(1, "duplicate_title")]


def test_page_problems_reports_every_failure_in_order():
    slots = [facts(), facts(active=False), facts(redistribution_ok=False)]
    assert page_problems(slots) == [(1, "inactive"), (2, "withheld")]


def test_unknown_series_is_a_problem_not_a_crash():
    assert page_problems([None]) == [(0, "unknown_series")]


def test_duplicate_title_of_a_dropped_slot_does_not_poison_the_next():
    """A slot dropped for another reason must not keep its title reserved."""
    broken = facts(has_served=False)
    same_title = facts()
    assert page_problems([broken, same_title]) == [(0, "no_served_value")]
