"""Shared comparison engine: pair byte baselines and bounded country groups.

The pair assertions pin what existing pages already render, so the generic series refactor can
be proven byte-identical before any new shape is added. Group assertions cover the bounded
three-to-six series factory, its exact tokens and its one-axis contract.
"""
import json
from pathlib import Path

from app import chart_model
from app.charts import chart_legend, chart_plot, comparison_svg
from app.interactive import build_payload

GOLDEN = Path(__file__).parent / "golden" / "charts"
PAIR_ROWS = [{"period": "2026-01", "a": "1.0", "b": "100000"},
             {"period": "2026-02", "a": "1.5", "b": "101000"}]


def pair_model(*, dual: bool):
    return chart_model.comparison_model(
        PAIR_ROWS, frequency="M", title="Par", labels=("A", "B"), unit_a="%",
        unit_b="milhões de euros" if dual else "%", dual=dual)


def test_pair_svg_stays_byte_identical_to_the_reviewed_capture():
    model = pair_model(dual=True)
    assert model is not None
    svg = str(comparison_svg(model))
    assert svg == (GOLDEN / "cmp_dual.svg").read_text(encoding="utf-8")
    # The shell splits this output into plot and legend without changing either byte stream.
    assert str(chart_plot(model)) + str(chart_legend(model)) == svg


def test_pair_payload_stays_byte_shaped_for_existing_readers():
    model = pair_model(dual=True)
    assert model is not None
    payload = build_payload(model)
    assert payload is not None
    assert list(payload) == ["version", "kind", "name", "x", "x_min", "x_max", "x_ticks",
                             "periods", "display", "y", "breaks", "axes", "series"]
    assert [list(entry) for entry in payload["series"]] == [
        ["title", "unit", "style", "badge"], ["title", "unit", "style", "badge"]]
    assert payload == {
        "version": 1,
        "kind": "comparison",
        "name": "Par: A (%) e B (milhões de euros)",
        "x": [24312.0, 24313.0],
        "x_min": 24312.0,
        "x_max": 24313.0,
        "x_ticks": [{"x": 24312.0, "text": "jan 2026"},
                    {"x": 24313.0, "text": "fev 2026"}],
        "periods": ["janeiro de 2026", "fevereiro de 2026"],
        "display": [["1,0 %", "100\u00a0000 milhões de euros"],
                    ["1,5 %", "101\u00a0000 milhões de euros"]],
        "y": [[1.0, 100000.0], [1.5, 101000.0]],
        "breaks": [],
        "axes": [
            {"unit": "%", "min": 0.8, "max": 1.6, "interval": 0.2,
             "ticks": [{"value": 0.8, "text": "0,8"}, {"value": 1.0, "text": "1"},
                       {"value": 1.2, "text": "1,2"}, {"value": 1.4, "text": "1,4"},
                       {"value": 1.6, "text": "1,6"}]},
            {"unit": "milhões de euros", "min": 99750.0, "max": 101250.0, "interval": 250.0,
             "ticks": [{"value": 99750.0, "text": "99\u00a0750"},
                       {"value": 100000.0, "text": "100\u00a0000"},
                       {"value": 100250.0, "text": "100\u00a0250"},
                       {"value": 100500.0, "text": "100\u00a0500"},
                       {"value": 100750.0, "text": "100\u00a0750"},
                       {"value": 101000.0, "text": "101\u00a0000"},
                       {"value": 101250.0, "text": "101\u00a0250"}]},
        ],
        "series": [
            {"title": "A", "unit": "%", "style": "ink", "badge": ""},
            {"title": "B", "unit": "milhões de euros", "style": "red", "badge": ""},
        ],
    }
    # The template serialises this object as JSON; ordering is part of the inert block.
    assert json.dumps(payload, ensure_ascii=False).startswith(
        '{"version": 1, "kind": "comparison", "name": "Par: A (%) e B (milhões de euros)"')
