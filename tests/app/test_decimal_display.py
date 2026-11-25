"""Reader precision is bounded; source and geometry precision remain separate."""
from decimal import Decimal, localcontext

import pytest

from app.formatting import format_axis, format_value


@pytest.mark.parametrize(("token", "expected"), [
    ("2.35673648910157", "2,36"),
    ("80.7926829268293", "80,79"),
    ("1234567.80", "1\u00a0234\u00a0567,8"),
    ("3.90", "3,9"),
    ("2.00", "2"),
    ("0.000000", "0"),
    ("-0.0", "0"),
    ("-2.345", "-2,35"),
    ("2.345", "2,35"),
    ("9.999", "10"),
    ("999.999", "1\u00a0000"),
    ("0.005", "0,01"),
    ("-0.005", "-0,01"),
    ("0.004", "< 0,01"),
    ("-0.004", "> -0,01"),
    ("1.234567e-8", "< 0,01"),
    ("8.07926829268293e1", "80,79"),
    ("123456789012345678901234567890.125", "123\u00a0456\u00a0789\u00a0012\u00a0345\u00a0678\u00a0901\u00a0234\u00a0567\u00a0890,13"),
])
def test_ui_values_have_at_most_two_decimal_places(token, expected):
    assert format_value(token) == expected


@pytest.mark.parametrize("token", ["n/d", "1,5", "NaN", "Infinity", ""])
def test_unknown_tokens_are_not_reinterpreted(token):
    assert format_value(token) == token


def test_ui_rounding_does_not_depend_on_or_modify_decimal_context():
    with localcontext() as context:
        context.prec = 3
        context.rounding = "ROUND_DOWN"
        assert format_value("123456.785") == "123\u00a0456,79"
        assert context.prec == 3
        assert context.rounding == "ROUND_DOWN"


@pytest.mark.parametrize("token", ["2.35673648910157", "80.7926829268293", "0.004"])
def test_page_rounds_display_without_rounding_geometry_or_csv(site_path, token):
    import hashlib

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
        exported = client.get(f"/series/{HICP}.csv")
        assert exported.status_code == 200
        assert f"2026-11;{token};" in exported.text
    assert hashlib.sha256(site_path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(("token", "expected"), [
    ("2.999", "3"), ("-2.345", "-2,35"), ("-0.0", "0"),
    ("0.004", "4e-3"), ("0.008", "8e-3"), ("-0.004", "-4e-3"),
])
def test_axis_labels_round_and_do_not_turn_small_ticks_into_zero(token, expected):
    assert format_axis(Decimal(token)) == expected
