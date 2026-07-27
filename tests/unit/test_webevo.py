from pathlib import Path

import numpy as np
from PIL import Image

from repath_evaluation.algorithms.webevo.matcher import (
    UPSTREAM_COMMIT,
    WebEvoMatcher,
    WebEvoParameters,
    _image_stages,
    _string_similarity,
)
from repath_evaluation.domain.models import (
    BoundingBox,
    DomNode,
    PagePair,
    PageSnapshot,
    PreDomNode,
)


def _node(node_id: int, *, tag: str, text: str, xpath: str) -> DomNode:
    return DomNode(
        list_index=node_id,
        node_id=node_id,
        element_id=node_id,
        parent_id=-1,
        element_type=2,
        tag=tag,
        text=text,
        xpath=xpath,
        bbox=BoundingBox(),
    )


def _pre(index: int, *, core: int, tag: str, text: str, xpath: str) -> PreDomNode:
    return PreDomNode(
        list_index=index,
        element_id=index,
        core_element_id=core,
        tag=tag,
        text=text,
        xpath=xpath,
        attributes={},
        bbox=BoundingBox(),
        displayed=True,
    )


def _write_pattern(path: Path, *, inverse: bool = False) -> None:
    array = np.zeros((32, 32, 3), dtype=np.uint8)
    array[:, 16:] = 255
    if inverse:
        array = 255 - array
    Image.fromarray(array, mode="RGB").save(path)


def test_webevo_is_pinned_to_author_repository_commit() -> None:
    assert UPSTREAM_COMMIT == "d195630b8dd5d85790d5aebb5c81c29bd03f01ca"


def test_webevo_uses_author_levenshtein_ratio() -> None:
    assert _string_similarity("kitten", "sitting") == 1 - 3 / 7


def test_webevo_image_pipeline_uses_candidate_inverse_as_third_stage() -> None:
    target_array = np.zeros((32, 32, 3), dtype=np.uint8)
    target_array[:, 16:] = 255
    candidate_array = 255 - target_array
    target = Image.fromarray(target_array, mode="RGB")
    candidate = Image.fromarray(candidate_array, mode="RGB")

    accepted, similarity, stage = _image_stages(target, candidate, WebEvoParameters())

    assert accepted is True
    assert similarity == 1.0
    assert stage == "candidate_inverse"


def test_webevo_candidates_follow_author_tag_group_order(tmp_path: Path) -> None:
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()
    source = _node(1, tag="a", text="", xpath="/html/body[1]/a[1]")
    new_nodes = [
        _node(10, tag="a", text="", xpath="/html/body[1]/a[1]"),
        _node(11, tag="div", text="", xpath="/html/body[1]/div[1]"),
    ]
    pre_nodes = [
        _pre(0, core=0, tag="a", text="", xpath=new_nodes[0].xpath),
        _pre(1, core=1, tag="div", text="", xpath=new_nodes[1].xpath),
    ]
    old = PageSnapshot("site", "old", old_root, [source], [], None, None)
    new = PageSnapshot("site", "new", new_root, new_nodes, pre_nodes, None, None)
    matcher = WebEvoMatcher()

    matcher.prepare(PagePair("site", tmp_path, old, new, {}, [], []))

    assert [candidate.tag for candidate in matcher._candidates] == ["div", "a"]


def test_webevo_nonempty_text_keeps_only_top_five(tmp_path: Path) -> None:
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()
    source = _node(1, tag="p", text="target", xpath="/html/body[1]/p[1]")
    new_nodes = [
        _node(10 + i, tag="p", text=f"target{i}", xpath=f"/html/body[1]/p[{i + 1}]")
        for i in range(7)
    ]
    old = PageSnapshot("site", "old", old_root, [source], [], None, None)
    new = PageSnapshot("site", "new", new_root, new_nodes, [], None, None)
    matcher = WebEvoMatcher()
    matcher.prepare(PagePair("site", tmp_path, old, new, {}, [], []))

    assert len(matcher._shortlist("target")) == 5


def test_webevo_matches_element_screenshots_without_external_runtime(tmp_path: Path) -> None:
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()
    source = _node(1, tag="p", text="Save", xpath="/html/body[1]/p[1]")
    candidate = _node(2, tag="p", text="Save", xpath="/html/body[1]/p[1]")
    _write_pattern(old_root / "1.png")
    _write_pattern(new_root / "2.png")
    old = PageSnapshot("site", "old", old_root, [source], [], None, None)
    new = PageSnapshot("site", "new", new_root, [candidate], [], None, None)
    matcher = WebEvoMatcher()
    matcher.prepare(PagePair("site", tmp_path, old, new, {}, [], []))

    result = matcher.match(1)

    assert result.top1 == 2
    assert "image_stage=original" in result.details
