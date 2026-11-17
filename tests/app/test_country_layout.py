"""Country-page layout and precise alignment wording regressions."""
from pathlib import Path

import pytest

from app.country_comparisons import alignment_text


@pytest.mark.parametrize(('dropped', 'opening'), [
    ((1, 0, 0, 0, 0), 'Fica de fora 1 período de Portugal'),
    ((2, 0, 0, 0, 0), 'Ficam de fora 2 períodos de Portugal'),
    ((1, 1, 0, 0, 0), 'Ficam de fora 1 período de Portugal e 1 período de Espanha'),
])
def test_dropped_periods_need_at_least_one_missing_country(dropped, opening):
    text = alignment_text(({'period': '2025'},), (0, 0, 0, 0, 0), dropped, 0,
                          ('Portugal', 'Espanha', 'França', 'Alemanha', 'Itália'), 'A')
    assert opening in text
    assert 'por faltar pelo menos um dos outros países em cada período.' in text
    assert 'sem par nos outros países' not in text


def test_summary_grid_never_requires_more_than_available_width():
    css = (Path(__file__).resolve().parents[2] / 'static/css/prumo.css').read_text()
    assert 'repeat(auto-fit, minmax(min(13rem, 100%), 1fr))' in css
