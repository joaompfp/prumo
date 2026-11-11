"""Shared observation-status vocabulary and the Eurostat flag mapping."""
import pytest

from ingest.flags import FLAGS, map_eurostat_flag


def test_vocabulary_is_closed_and_ordered():
    assert FLAGS == ("normal", "provisional", "estimated", "revised", "break")


@pytest.mark.parametrize("code, flag", [
    (None, "normal"), ("", "normal"), (" ", "normal"),
    ("p", "provisional"),
    ("e", "estimated"), ("s", "estimated"), ("f", "estimated"), ("u", "estimated"),
    ("n", "estimated"), ("i", "estimated"),
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


@pytest.mark.parametrize("code", ["x", "P", "pq", "1", "p,", "a"])
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


@pytest.mark.parametrize("code", ["x", "w", ": q"])
def test_missing_value_rows_still_reject_unknown_codes(code):
    with pytest.raises(ValueError):
        map_eurostat_flag(code, value_present=False)


def test_every_mapped_result_is_in_the_vocabulary():
    for code in "pesfunirbd":
        assert map_eurostat_flag(code) in FLAGS


# --- confidentiality part (SDMX CONF_STATUS, after '|') ----------------------------------------

from ingest.flags import split_eurostat_status  # noqa: E402


@pytest.mark.parametrize("status, parts", [
    (None, ("", None)), ("", ("", None)), ("p", ("p", None)), ("bp", ("bp", None)),
    ("|C", ("", "C")), ("|N", ("", "N")), ("b|C", ("b", "C")), ("pe|N", ("pe", "N")),
    ("p|", ("p", None)),
])
def test_split_status(status, parts):
    assert split_eurostat_status(status) == parts


@pytest.mark.parametrize("status", ["|X", "|c", "p|CC", "|C|N", "b|Z"])
def test_unknown_confidentiality_code_raises(status):
    with pytest.raises(ValueError, match="confidentiality"):
        split_eurostat_status(status)


def test_flag_mapping_refuses_an_unsplit_status():
    with pytest.raises(ValueError):
        map_eurostat_flag("|C")
