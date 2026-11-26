"""Discovery selection boundary: bounded lenient references and the shared URL helper.

The discovery page accepts more references than the notebook (for recovery across a 24-result
page) but still refuses an unbounded address before any database work. The notebook's own parser
keeps its strict twelve-raw-parameter contract; these tests name both so one cannot quietly
replace the other.
"""
from urllib.parse import parse_qs, urlsplit

from app import discovery_selection, notebook


def test_discovery_parser_accepts_ordered_unique_references_through_48():
    assert discovery_selection.parse_references([]) == ()
    assert discovery_selection.parse_references(["b", "a", "b"]) == ("b", "a")
    assert discovery_selection.parse_references(["a.b-c_d", "S_2.0"]) == ("a.b-c_d", "S_2.0")

    boundary = [f"s{i}" for i in range(48)]
    parsed = discovery_selection.parse_references(boundary)
    assert parsed == tuple(boundary)
    assert discovery_selection.parse_references([f"s{i}" for i in range(49)]) is None
    # The ceiling is on raw parameters, before deduplication.
    assert discovery_selection.parse_references(["a"] * 49) is None
    # Thirteen unique references are recoverable on discovery, unlike the notebook's strict parser.
    thirteen = [f"s{i}" for i in range(13)]
    assert len(discovery_selection.parse_references(thirteen)) == 13
    assert notebook.parse_selection(thirteen) is None


def test_discovery_parser_rejects_malformed_references():
    for malformed in ("", "a b", "a/b", "a#b", "../a", "a\nb", "x" * 256):
        assert discovery_selection.parse_references([malformed]) is None


def test_retiring_references_removes_only_named_values_and_preserves_order():
    selection = ("a", "b", "c")
    assert discovery_selection.retire(selection, ["b"]) == ("a", "c")
    assert discovery_selection.retire(selection, ["b", "b"]) == ("a", "c")
    assert discovery_selection.retire(selection, ["missing"]) == selection
    # A malformed control value is not an address error and cannot remove an arbitrary reference.
    assert discovery_selection.retire(selection, ["a/b", ""]) == selection


def test_shared_address_helper_keeps_first_order_and_omits_empty_values():
    assert discovery_selection.build_address("/pesquisa", []) == "/pesquisa"
    assert discovery_selection.build_address(
        "/pesquisa", [("s", "b"), ("q", ""), ("s", "a")]) == "/pesquisa?s=b&s=a"
    encoded = discovery_selection.build_address(
        "/pesquisa", [("s", "a"), ("q", "a&b"), ("g", "a")])
    assert "q=a%26b" in encoded
    assert parse_qs(urlsplit(encoded).query) == {"s": ["a"], "q": ["a&b"], "g": ["a"]}
