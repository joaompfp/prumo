"""Focused contract for the notebook chart address: bounded settings, paths and pruning.

These are pure tests: no database, no templates. The route passes the same `getlist` shape the
Starlette query object exposes, so repeated singleton abuse is exercised exactly as it arrives.
"""
from starlette.datastructures import QueryParams

from app import notebook
from app.notebook_chart import (
    MAX_GROUP,
    PARAM_NAMES,
    ChartSettings,
    parse_settings,
    without_side,
)


def parse(query: str, selection: tuple[str, ...] = ("a", "b")) -> ChartSettings | None:
    values = QueryParams(query)
    return parse_settings({name: values.getlist(name) for name in PARAM_NAMES}, selection)


def test_absent_chart_parameters_are_the_bounded_default():
    settings = parse("")
    assert settings == ChartSettings()
    assert settings.mode == "all"
    assert settings.scale == "comum"
    assert settings.window == "10a"
    assert settings.day is None
    assert settings.params() == []


def test_explicit_empty_is_not_all_and_off_is_not_empty():
    assert parse("grafico=on") == ChartSettings(mode="explicit", group=())
    assert parse("grafico=on").params() == [("grafico", "on")]
    assert parse("g=b&g=a&g=b") == ChartSettings(mode="explicit", group=("b", "a"))
    assert parse("grafico=off") == ChartSettings(mode="off", group=())
    # `g` alone is still an explicit subset, and off wins over it without becoming all.
    assert parse("g=a") == ChartSettings(mode="explicit", group=("a",))
    assert parse("grafico=off&g=a") == ChartSettings(mode="off", group=())


def test_group_is_bounded_and_must_belong_to_the_addressed_selection():
    assert parse("g=a&g=a&g=b").group == ("a", "b")
    assert parse("g=a&g=z") is None
    assert parse("g=") is None
    six = "&".join(f"g={item}" for item in ("a", "a", "b", "b", "a", "b"))
    assert parse(six).group == ("a", "b")
    seven = "&".join(["g=a"] * (MAX_GROUP + 1))
    assert parse(seven) is None


def test_malformed_and_repeated_singletons_are_invalid_addresses():
    for query in (
        "grafico=yes",
        "grafico=on&grafico=off",
        "escala=mista",
        "escala=comum&escala=dupla",
        "janela=20a",
        "janela=max&janela=5a",
        "dia=2026-1-1",
        "dia=2026-02-30",
        "dia=2026-11-01&dia=2026-11-02",
        "escala=",
        "janela=",
    ):
        assert parse(query) is None, query


def test_valid_day_scale_and_window_are_kept_for_sharing():
    settings = parse("escala=dupla&janela=5a&dia=2026-11-01")
    assert settings == ChartSettings(scale="dupla", window="5a", day="2026-11-01")
    assert settings.params() == [("escala", "dupla"), ("janela", "5a"),
                                 ("dia", "2026-11-01")]
    assert parse("dia=").day is None


def test_deliberate_removal_prunes_only_the_explicit_group():
    settings = ChartSettings(mode="explicit", group=("a", "b"), scale="dupla", window="5a")
    pruned = without_side(settings, "a")
    assert pruned.group == ("b",)
    assert pruned.mode == "explicit"
    assert pruned.scale == "dupla" and pruned.window == "5a"
    last = without_side(pruned, "b")
    assert last.mode == "off" and last.group == ()
    # Removing a side that is not in the group, or an implicit-all address, changes nothing.
    assert without_side(settings, "c") == settings
    assert without_side(ChartSettings(), "a") == ChartSettings()
    assert without_side(ChartSettings(mode="off"), "a") == ChartSettings(mode="off")


def test_links_carry_chart_settings_in_a_stable_order_and_omit_defaults():
    default = ChartSettings()
    assert notebook.selection_path(("a", "b"), chart=default) == "/caderno?s=a&s=b"
    explicit = ChartSettings(mode="explicit", group=("b", "a"), scale="dupla", window="5a",
                             day="2026-11-01")
    assert notebook.selection_path(("a", "b"), "termo", chart=explicit) == (
        "/caderno?s=a&s=b&grafico=on&g=b&g=a&escala=dupla&janela=5a&dia=2026-11-01&q=termo")
    off = ChartSettings(mode="off", scale="dupla", window="max")
    assert notebook.selection_path(("a",), chart=off) == (
        "/caderno?s=a&grafico=off&escala=dupla&janela=max")
    # The old one-argument form used by the series pages is untouched.
    assert notebook.selection_path(("a",)) == "/caderno?s=a"
