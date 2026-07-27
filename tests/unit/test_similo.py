from pathlib import Path

import pytest

from repath_evaluation.algorithms.similo import UPSTREAM_COMMIT, SimiloMatcher
from repath_evaluation.domain.models import BoundingBox, DomNode, PagePair, PageSnapshot


def node(
    index,
    node_id,
    text,
    *,
    tag="button",
    x=0,
    y=0,
    width=100,
    height=20,
    attributes=None,
    explicit_id="",
    parent_id=-1,
    displayed=True,
    xpath=None,
    raw=None,
):
    return DomNode(
        list_index=index,
        node_id=node_id,
        element_id=node_id,
        parent_id=parent_id,
        element_type=2,
        tag=tag,
        text=text,
        xpath=xpath or f"/html[1]/body[1]/{tag}[{index + 1}]",
        attributes=attributes or {},
        bbox=BoundingBox(x, y, width, height),
        displayed=displayed,
        explicit_id=explicit_id,
        raw=raw or {},
    )


def pair(old_nodes, new_nodes):
    old = PageSnapshot("site", "old", Path("."), old_nodes, [], None, None)
    new = PageSnapshot("site", "new", Path("."), new_nodes, [], None, None)
    return PagePair("site", Path("."), old, new, {}, [], [])


def test_similo_is_pinned_to_original_author_repository_commit():
    assert UPSTREAM_COMMIT == "743ddede7df92814ddc3fb7f96e09bdb508e285a"


def test_similo_prefers_exact_id_and_text():
    old_nodes = [node(0, 0, "Save", explicit_id="save")]
    new_nodes = [
        node(0, 0, "Cancel", x=20, y=20, explicit_id="cancel"),
        node(1, 1, "Save", x=200, y=200, explicit_id="save"),
    ]
    matcher = SimiloMatcher()
    matcher.prepare(pair(old_nodes, new_nodes))
    assert matcher.match(0).top1 == 1


def test_string_similarity_matches_author_normalization_and_integer_rounding():
    # Metadata is lower-cased before comparison.
    assert SimiloMatcher._string_similarity("SAVE", "save") == 1.0
    # Punctuation is stripped only for Levenshtein distance.
    assert SimiloMatcher._string_similarity("a-b", "ab") == 1.0
    # Java integer arithmetic floors 5/6 to 83 percent.
    assert SimiloMatcher._string_similarity("abcdef", "abcxef") == 0.83


def test_visible_text_uses_valid_text_then_value_then_placeholder_only():
    short_text = node(
        0,
        0,
        "Hi",
        attributes={"value": "Submit", "placeholder": "Fallback", "aria-label": "Ignored"},
    )
    long_text = node(
        1,
        1,
        "x" * 51,
        attributes={"placeholder": "Search here", "title": "Ignored"},
    )
    assert SimiloMatcher._visible_text(short_text) == "submit"
    assert SimiloMatcher._visible_text(long_text) == "search here"


def test_candidate_filter_matches_author_query_and_visibility_rules():
    assert SimiloMatcher._eligible(node(0, 0, "ok", tag="button"))
    assert not SimiloMatcher._eligible(node(0, 0, "ok", tag="section"))
    assert not SimiloMatcher._eligible(node(0, 0, "ok", width=0))
    assert not SimiloMatcher._eligible(node(0, 0, "ok", displayed=False))


def test_location_similarity_truncates_pixel_distance_before_scoring():
    left = node(0, 0, "left", x=0, y=0)
    right = node(1, 1, "right", x=5, y=5)
    # sqrt(50) is truncated to 7 by the Java implementation.
    assert SimiloMatcher._location_similarity(left, right) == 0.93


def test_id_xpath_uses_nearest_unique_ancestor_id():
    parent = node(
        0,
        10,
        "parent",
        tag="div",
        explicit_id="Panel",
        xpath="/html[1]/body[1]/div[1]",
    )
    child = node(
        1,
        11,
        "child",
        tag="span",
        parent_id=10,
        xpath="/html[1]/body[1]/div[1]/span[1]",
    )
    snapshot = PageSnapshot("site", "old", Path("."), [parent, child], [], None, None)
    id_xpaths = SimiloMatcher._build_id_xpath_map(snapshot)
    assert id_xpaths[child.list_index] == "//*[@id='panel']/span[1]"


def test_id_xpath_uses_first_duplicate_id_like_document_get_element_by_id():
    first = node(
        0,
        10,
        "first",
        tag="div",
        explicit_id="duplicate",
        xpath="/html[1]/body[1]/div[1]",
    )
    second = node(
        1,
        11,
        "second",
        tag="div",
        explicit_id="duplicate",
        xpath="/html[1]/body[1]/div[2]",
    )
    snapshot = PageSnapshot("site", "old", Path("."), [first, second], [], None, None)
    id_xpaths = SimiloMatcher._build_id_xpath_map(snapshot)
    assert id_xpaths[first.list_index] == "//*[@id='duplicate']"
    assert id_xpaths[second.list_index] == "/html[1]/body[1]/div[2]"


def test_neighbor_similarity_preserves_integer_percent_rounding():
    assert SimiloMatcher._neighbour_similarity("save now", "save later") == 0.44


def test_score_uses_fourteen_author_properties():
    old = node(
        0,
        0,
        "Save",
        explicit_id="save",
        attributes={"class": "primary", "name": "submit", "type": "submit"},
    )
    new = node(
        0,
        1,
        "Save",
        explicit_id="save",
        attributes={"class": "primary", "name": "submit", "type": "submit"},
    )
    matcher = SimiloMatcher()
    matcher.prepare(pair([old], [new]))
    # All available properties match; absent href/alt/neighbor properties add zero.
    assert matcher.score(old, new) == pytest.approx(9.5)
