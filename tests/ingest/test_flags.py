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


# --- INE (Statistics Portugal) conventional signs ('sinal_conv' + 'sinal_conv_desc') -------------
from ingest.flags import INE_NO_VALUE_SIGNS, INE_VALUE_SIGNS, map_ine_flag  # noqa: E402


def test_ine_no_sign_on_a_value_is_normal():
    assert map_ine_flag(None, None) == "normal"
    assert map_ine_flag("", "") == "normal"


def test_ine_provisional_sign():
    # live: 0007983 (monthly unemployment rate, SA) 'ind_string': '5,0 &', 'valor': '5'
    assert map_ine_flag("&", "Dado provisório") == "provisional"


@pytest.mark.parametrize("sign, desc", [("x", "Dado não disponível"),
                                        ("-", "Dado nulo ou não aplicável")])
def test_ine_no_value_signs_give_no_flag(sign, desc):
    assert map_ine_flag(sign, desc, value_present=False) is None


@pytest.mark.parametrize("sign, desc", [("x", "Dado não disponível"),
                                        ("-", "Dado nulo ou não aplicável")])
def test_ine_no_value_sign_on_a_value_raises(sign, desc):
    with pytest.raises(ValueError):
        map_ine_flag(sign, desc)


def test_ine_value_sign_without_a_value_raises():
    with pytest.raises(ValueError):
        map_ine_flag("&", "Dado provisório", value_present=False)


def test_ine_missing_value_without_any_sign_raises():
    with pytest.raises(ValueError):
        map_ine_flag(None, None, value_present=False)


@pytest.mark.parametrize("sign, desc", [("Po", "Dado provisório"), ("?", None), ("&", None),
                                        ("&", "Dado estimado"), ("x", "Dado confidencial"),
                                        (None, "Dado provisório")])
def test_ine_unknown_sign_or_changed_meaning_raises(sign, desc):
    # a sign is only trusted together with its reviewed description
    with pytest.raises(ValueError):
        map_ine_flag(sign, desc, value_present=sign in INE_VALUE_SIGNS)


def test_ine_tables_are_disjoint_and_map_into_the_vocabulary():
    assert not set(INE_VALUE_SIGNS) & set(INE_NO_VALUE_SIGNS)
    assert {flag for flag, _ in INE_VALUE_SIGNS.values()} <= set(FLAGS)
