"""Shared observation-status vocabulary and the Eurostat flag mapping."""
import pytest

from ingest.flags import FLAGS, map_eurostat_flag


def test_vocabulary_is_closed_and_ordered():
    assert FLAGS == ("normal", "provisional", "estimated", "revised", "break")


@pytest.mark.parametrize("code, flag", [
    (None, "normal"), ("", "normal"), (" ", "normal"),
    ("p", "provisional"),
    ("e", "estimated"), ("s", "estimated"), ("f", "estimated"), ("u", "estimated"),
    ("n", "estimated"),
    ("r", "revised"),
    ("b", "break"), ("d", "break"),
])
def test_single_codes(code, flag):
    assert map_eurostat_flag(code) == flag


@pytest.mark.parametrize("code, flag", [
    ("bp", "break"), ("pb", "break"), ("ep", "provisional"), ("pe", "provisional"),
    ("re", "estimated"), ("rp", "provisional"), ("de", "break"), (" p ", "provisional"),
    ("b p", "break"),
])
def test_combined_codes_take_the_strongest(code, flag):
    assert map_eurostat_flag(code) == flag


@pytest.mark.parametrize("code", ["x", "i", "P", "pq", "1", "p,"])
def test_unknown_codes_raise(code):
    with pytest.raises(ValueError):
        map_eurostat_flag(code)


@pytest.mark.parametrize("code", ["c", "z", ":", ": c", "cp"])
def test_no_value_markers_never_qualify_a_value(code):
    # confidential / not applicable / not available only ever accompany a missing value
    with pytest.raises(ValueError):
        map_eurostat_flag(code)


@pytest.mark.parametrize("code", [None, "", "c", "z", ":", ": c", "p", "bp"])
def test_missing_value_rows_accept_known_codes_and_return_none(code):
    assert map_eurostat_flag(code, value_present=False) is None


@pytest.mark.parametrize("code", ["x", "i", ": q"])
def test_missing_value_rows_still_reject_unknown_codes(code):
    with pytest.raises(ValueError):
        map_eurostat_flag(code, value_present=False)


def test_every_mapped_result_is_in_the_vocabulary():
    for code in "pesfunrbd":
        assert map_eurostat_flag(code) in FLAGS
