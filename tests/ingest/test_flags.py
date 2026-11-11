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


# --- the full official legend (M2, fix round 1) -------------------------------------------------
# Sign/description pairs below are the official legend of
# https://www.ine.pt/bddXplorer/htdocs/sinais.jsp (recorded live 2026-11-11 in
# tests/ingest/fixtures/ine/verify/sinais_PT.html); '&', 'x' and '-' were also observed in live
# JSON payloads (sinal_conv_desc 'Dado provisório'/'Dado não disponível'/'Dado nulo ou não
# aplicável').
import re  # noqa: E402
from pathlib import Path  # noqa: E402

LEGEND = Path(__file__).resolve().parent / "fixtures" / "ine" / "verify" / "sinais_PT.html"


def _legend() -> dict[str, list[tuple[str, str]]]:
    """sinais.jsp -> {section title: [(sign, description)]}, verbatim."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", LEGEND.read_text(encoding="utf-8"), re.S)
    out: dict[str, list[tuple[str, str]]] = {}
    section = None
    for row in rows:
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        cells = [c for c in cells if c]
        if len(cells) == 1:
            section = cells[0]
        elif len(cells) == 2 and section:
            out.setdefault(section, []).append((cells[0], cells[1]))
    return out


@pytest.mark.parametrize("sign, desc, flag", [
    ("//", "Dado preliminar", "provisional"),
    ("*", "Dado rectificado", "revised"),
    ("┴", "Quebra de série/comparabilidade", "break"),
    ("“", "Estimativa", "estimated"),
    # quality caveat: mapped to 'normal' BY DECISION (M2); the caveat text is lost
    ("§", "Desvio do padrão de qualidade/Coeficiente de variação elevado", "normal"),
])
def test_ine_additional_value_signs(sign, desc, flag):
    assert map_ine_flag(sign, desc) == flag


def test_ine_confidential_sign_stands_for_a_missing_value():
    assert map_ine_flag("…", "Dado confidencial", value_present=False) is None
    with pytest.raises(ValueError):  # a no-value sign never qualifies a published value
        map_ine_flag("…", "Dado confidencial")


@pytest.mark.parametrize("sign", ["o", "∞", "»", "i", "“E"])
def test_ine_reviewed_but_unmapped_signs_raise(sign):
    # in the official legend but deliberately UNMAPPED: the first live observation must fail
    # loudly and force a mapping review, never silently pass as a normal value
    with pytest.raises(ValueError, match="unknown INE"):
        map_ine_flag(sign, "qualquer descrição")
    with pytest.raises(ValueError, match="unknown INE"):
        map_ine_flag(sign, "qualquer descrição", value_present=False)


def test_ine_mapped_pairs_are_the_official_legend():
    """Every mapped sign appears in sinais.jsp with exactly the mapped description, in the right
    absence-of-value/additional-to-value section; every sign in those two sections is either
    mapped or in the explicit reviewed-but-unmapped set above."""
    legend = _legend()
    absent = dict(legend["Sinais convencionais por ausência de valor"])
    added = dict(legend["Sinais convencionais adicionais ao valor"])
    assert INE_NO_VALUE_SIGNS == {s: absent[s] for s in INE_NO_VALUE_SIGNS}
    for sign, (_, desc) in INE_VALUE_SIGNS.items():
        assert added[sign] == desc, sign
    unmapped = {"o", "∞", "»", "i", "“E"}
    assert (set(absent) | set(added)) - set(INE_VALUE_SIGNS) - set(INE_NO_VALUE_SIGNS) == unmapped


# --- Banco de Portugal (BPstat JSON-stat `status`) ------------------------------------------------
# Vocabulary observed live (2026-11-11): every valued cell of all 10 core series (full history,
# ~33,400 cells over the 5 datasets) and of a national-accounts probe carries 'F'; valueless
# cells (e.g. DE 10y before 2000-01) carry status null. No code legend is published in the API
# docs (OpenAPI types status as a nullable string), so the mapping is fail-closed: 'F' -> normal;
# anything else raises for review, on valued AND valueless cells alike.

from ingest.flags import map_bportugal_flag  # noqa: E402


def test_bportugal_final_status_maps_to_normal():
    assert map_bportugal_flag("F") == "normal"


def test_bportugal_valueless_cells_have_no_status():
    assert map_bportugal_flag(None, value_present=False) is None


@pytest.mark.parametrize("status", ["P", "E", "B", "R", "C", "N", "f", "Provisional", ""])
def test_bportugal_unknown_status_codes_raise(status):
    with pytest.raises(ValueError, match="BPstat"):
        map_bportugal_flag(status)


def test_bportugal_valued_cell_without_status_raises():
    with pytest.raises(ValueError, match="BPstat"):
        map_bportugal_flag(None)


def test_bportugal_status_on_a_valueless_cell_raises():
    # 'F' claims a published state for a value that is not there: misread or format change.
    with pytest.raises(ValueError, match="BPstat"):
        map_bportugal_flag("F", value_present=False)
