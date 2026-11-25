"""Reader precision is bounded; source and geometry precision remain separate."""
from decimal import Decimal, localcontext

import pytest

from app.formatting import format_axis, format_value


@pytest.mark.parametrize(("token", "expected"), [
    ("2.35673648910157", "2,357"),
    ("80.7926829268293", "80,79"),
    ("1234567.80", "1\u00a0235\u00a0000"),
    ("12345", "12\u00a0350"),
    ("1234.56", "1\u00a0235"),
    ("123.456", "123,5"),
    ("12.3456", "12,35"),
    ("1.23456", "1,235"),
    ("0.123456", "0,1235"),
    ("0.0123456", "0,01235"),
    ("0.00123456", "0,001235"),
    ("0.000123456", "0,0001235"),
    ("3.90", "3,9"),
    ("2.00", "2"),
    ("1000.00", "1\u00a0000"),
    ("0.000000", "0"),
    ("-0.0", "0"),
    ("-2.3445", "-2,345"),
    ("2.3445", "2,345"),
    ("-2.3455", "-2,346"),
    ("2.3455", "2,346"),
    ("9.9999", "10"),
    ("999.999", "1\u00a0000"),
    ("9999.9", "10\u00a0000"),
    ("999999999999.9", "1e12"),
    ("0.005", "0,005"),
    ("-0.005", "-0,005"),
    ("0.004", "0,004"),
    ("-0.004", "-0,004"),
    ("1.234567e-8", "1,235e-8"),
    ("9.9999e-7", "0,000001"),
    ("8.07926829268293e1", "80,79"),
    ("123456789012345678901234567890.125", "1,235e29"),
    ("1e10000", "1e10000"),
    ("1e-10000", "1e-10000"),
])
def test_ui_values_have_at_most_four_significant_figures(token, expected):
    assert format_value(token) == expected


def test_svg_rounding_changes_only_the_reviewed_tick_text():
    from pathlib import Path
    from xml.etree import ElementTree

    golden = Path(__file__).parent / "golden" / "charts"
    before = ElementTree.fromstring(
        "<capture>" + (golden / "pre_significant_figures/cmp_dual.svg").read_text() + "</capture>")
    after = ElementTree.fromstring(
        "<capture>" + (golden / "cmp_dual.svg").read_text() + "</capture>")
    previous, current = list(before.iter()), list(after.iter())
    assert len(previous) == len(current)
    changed = []
    for old, new in zip(previous, current):
        assert (old.tag, old.attrib, old.tail) == (new.tag, new.attrib, new.tail)
        if old.text != new.text:
            assert old.tag == "text" and old.attrib.get("class") == "chart-tick"
            changed.append((old.text, new.text))
    assert changed == [("100\u00a0250", "100\u00a0300"),
                       ("100\u00a0750", "100\u00a0800"),
                       ("101\u00a0250", "101\u00a0300")]


@pytest.mark.parametrize("token", ["n/d", "1,5", "NaN", "Infinity", ""])
def test_unknown_tokens_are_not_reinterpreted(token):
    assert format_value(token) == token


def test_ui_rounding_does_not_depend_on_or_modify_decimal_context():
    with localcontext() as context:
        context.prec = 3
        context.rounding = "ROUND_DOWN"
        context.Emin, context.Emax = -9, 9
        assert format_value("123456.785") == "123\u00a0500"
        assert format_value("1.234567e-100") == "1,235e-100"
        assert format_value("1.234567e100") == "1,235e100"
        assert context.prec == 3
        assert context.rounding == "ROUND_DOWN"
        assert (context.Emin, context.Emax) == (-9, 9)


@pytest.mark.parametrize("exponent", range(-12, 16))
@pytest.mark.parametrize("sign", ("", "-"))
def test_precision_is_relative_across_orders_of_magnitude(exponent, sign):
    value = Decimal(f"{sign}1.23456789e{exponent}")
    text = format_value(str(value))
    displayed = Decimal(text.replace("\u00a0", "").replace(",", "."))
    assert displayed == Decimal(f"{sign}1.235e{exponent}")
    assert len(displayed.normalize().as_tuple().digits) <= 4
    assert displayed != 0


@pytest.mark.parametrize("token", ["2.35673648910157", "80.7926829268293", "0.004",
                                   "0.000123456", "1234567.80"])
def test_page_rounds_display_without_rounding_geometry_or_csv(site_path, token):
    import hashlib
    from html import escape

    from fastapi.testclient import TestClient

    from app.main import create_app
    from ingest.db import open_db
    from tests.app.conftest import HICP, T4, fetch
    from tests.app.test_interactive import payload_of

    db = open_db(site_path)
    fetch(db, HICP, {"2026-11": token}, T4)
    db.close()
    before = hashlib.sha256(site_path.read_bytes()).hexdigest()
    with TestClient(create_app(str(site_path))) as client:
        response = client.get(f"/series/{HICP}")
        assert response.status_code == 200
        payload = payload_of(response.text)
        assert payload["display"][-1] == [format_value(token) + " %"]
        assert payload["y"][-1] == [float(token)]
        assert f'<td class="num">{escape(format_value(token))}</td>' in response.text
        assert (f'class="figure-value">{escape(format_value(token))} '
                '<span class="figure-unit">') in response.text
        exported = client.get(f"/series/{HICP}.csv")
        assert exported.status_code == 200
        assert f"2026-11;{token};" in exported.text
    assert hashlib.sha256(site_path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(("token", "expected"), [
    ("2.999", "2,999"), ("-2.3455", "-2,346"), ("-0.0", "0"),
    ("0.004", "4e-3"), ("0.008", "8e-3"), ("-0.004", "-4e-3"),
    ("0.00123456", "1,235e-3"), ("123456.789", "123\u00a0500"),
])
def test_axis_labels_share_significant_precision_and_keep_tiny_ticks_nonzero(token, expected):
    assert format_axis(Decimal(token)) == expected
