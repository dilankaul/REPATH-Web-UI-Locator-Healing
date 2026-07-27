from pathlib import Path

import pytest

from repath_evaluation.algorithms.water import UPSTREAM_COMMIT, WaterMatcher
from repath_evaluation.domain.models import BoundingBox, DomNode, PagePair, PageSnapshot, PreDomNode


def _pair(old_pre, new_pres, new_groups):
    old_group = DomNode(0, 0, old_pre.element_id, -1, 2, old_pre.tag, "", old_pre.xpath)
    old = PageSnapshot("site", "old", Path("."), [old_group], [old_pre], None, None)
    new = PageSnapshot("site", "new", Path("."), new_groups, new_pres, None, None)
    return PagePair("site", Path("."), old, new, {0: 0}, [], [])


def test_water_is_pinned_to_original_author_repository_commit():
    assert UPSTREAM_COMMIT == "c57311e56afb8e52ccd315e460e1a6f5084a7b95"


def test_water_exact_id_and_group_conversion():
    old_pre = PreDomNode(10, 10, 10, "input", "", "/old", {}, BoundingBox(), True, "target", "")
    matched_new_pre = PreDomNode(5, 5, 20, "input", "", "/new-leaf", {}, BoundingBox(), True, "target", "")
    core_new_pre = PreDomNode(20, 20, 20, "input", "", "/new-core", {}, BoundingBox(), True, "", "")
    new_group = DomNode(0, 0, 20, -1, 2, "input", "", "/new-core")
    matcher = WaterMatcher()
    matcher.prepare(_pair(old_pre, [matched_new_pre, core_new_pre], [new_group]))
    assert matcher.match(0).top1 == 0


def test_water_exact_matching_is_union_not_property_priority_short_circuit():
    old_pre = PreDomNode(0, 10, 10, "input", "", "/old", {"class": "same"}, BoundingBox(), True, "best-id", "")
    class_match = PreDomNode(0, 20, 20, "input", "", "/class", {"class": "same"}, BoundingBox(), True, "", "")
    id_match = PreDomNode(1, 30, 30, "input", "", "/id", {}, BoundingBox(), True, "best-id", "")
    core_class = PreDomNode(2, 20, 20, "input", "", "/core-class", {}, BoundingBox(), True)
    core_id = PreDomNode(3, 30, 30, "input", "", "/core-id", {}, BoundingBox(), True)
    groups = [
        DomNode(0, 100, 20, -1, 2, "input", "", "/core-class"),
        DomNode(1, 101, 30, -1, 2, "input", "", "/core-id"),
    ]
    matcher = WaterMatcher()
    matcher.prepare(_pair(old_pre, [class_match, id_match, core_class, core_id], groups))
    result = matcher.match(0)
    assert [item.node_id for item in result.ranking] == [100, 101]


def test_water_link_text_uses_link_text_field_not_generic_text():
    source = PreDomNode(0, 0, 0, "a", "shared body text", "/a", {}, BoundingBox(), True, raw={"linkText": "Open"})
    wrong = PreDomNode(1, 1, 1, "a", "shared body text", "/b", {}, BoundingBox(), True, raw={"linkText": "Close"})
    right = PreDomNode(2, 2, 2, "a", "different body text", "/c", {}, BoundingBox(), True, raw={"linkText": "Open"})
    assert not WaterMatcher._has_exact_property_match(source, wrong)
    assert WaterMatcher._has_exact_property_match(source, right)


def test_water_similarity_uses_all_five_rho2_components():
    source = PreDomNode(
        0, 0, 0, "div", "", "/a", {}, BoundingBox(10, 20, 30, 40), True,
        raw={"clickable": True, "zIndex": 3},
    )
    same = PreDomNode(
        1, 1, 1, "div", "", "/b", {}, BoundingBox(10, 20, 30, 40), True,
        raw={"clickable": True, "zIndex": 3},
    )
    different = PreDomNode(
        2, 2, 2, "div", "", "/b", {}, BoundingBox(10, 20, 50, 60), False,
        raw={"clickable": False, "zIndex": 8},
    )
    assert WaterMatcher._similarity(source, same) == pytest.approx(0.53)
    assert WaterMatcher._similarity(source, different) == pytest.approx(0.45)
