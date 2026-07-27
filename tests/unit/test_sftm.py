from pathlib import Path

from repath_evaluation.algorithms.sftm.matcher import (
    UPSTREAM_COMMIT,
    SftmMatcher,
    SftmParameters,
    _InMemoryIndex,
    _Node,
    _add_parent_tokens,
    _author_xpath_key,
    _dataset_xpath_key,
    _parse_html,
    _parse_snapshot,
)
from repath_evaluation.domain.models import BoundingBox, DomNode, PagePair, PageSnapshot


def _dom_node(node_id: int, xpath: str) -> DomNode:
    return DomNode(
        list_index=node_id,
        node_id=node_id,
        element_id=node_id,
        parent_id=-1,
        element_type=2,
        tag="button",
        text="",
        xpath=xpath,
        attributes={},
        bbox=BoundingBox(),
    )


def _pair(tmp_path: Path, old_html: str, new_html: str) -> PagePair:
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()
    old_path = old_root / "old.html"
    new_path = new_root / "new.html"
    old_path.write_text(old_html, encoding="utf-8")
    new_path.write_text(new_html, encoding="utf-8")
    old = PageSnapshot(
        "site",
        "old",
        old_root,
        [_dom_node(10, "/html/body[1]/button[1]")],
        [],
        None,
        old_path,
    )
    new = PageSnapshot(
        "site",
        "new",
        new_root,
        [_dom_node(20, "/html/body[1]/button[1]")],
        [],
        None,
        new_path,
    )
    return PagePair("site", tmp_path, old, new, {10: 20}, [], [])


def test_sftm_is_pinned_to_author_repository_commit() -> None:
    assert UPSTREAM_COMMIT == "4f8683b0e5a21050d1679f1c350f558a5a4171e5"


def test_dom_parser_matches_author_body_tree_and_zero_based_xpath() -> None:
    nodes = _parse_html(
        "<html><body><h1>A</h1><div><p>p1</p><p>p2</p></div></body></html>",
        SftmParameters(),
    )

    assert [node.xpath for node in nodes] == [
        "/body",
        "/body/h1[0]",
        "/body/div[0]",
        "/body/div[0]/p[0]",
        "/body/div[0]/p[1]",
    ]


def test_dom_parser_matches_author_attribute_tokenization() -> None:
    nodes = _parse_html(
        '<html><body><button signature="42" data-id="ignored" '
        'aria-label="Save item" disabled>Save</button></body></html>',
        SftmParameters(),
    )
    tokens = nodes[1].tokens

    assert "signature" not in tokens
    assert not any(token.startswith("data-id") for token in tokens)
    assert {"aria-label:Save", "aria-label:item", "aria-label:Save item", "aria-label"} <= set(tokens)
    assert "disabled" in tokens
    assert "Save" not in tokens  # visible text is not an SFTM label token


def test_author_xpath_maps_to_dataset_one_based_xpath() -> None:
    assert _author_xpath_key("/body/div[0]/span[2]") == _dataset_xpath_key(
        "/html/body[1]/div[1]/span[3]"
    )


def test_index_preserves_author_ascending_top_n_quirk() -> None:
    sources = [
        _Node(0, ["rare", "common"], "/body/div[0]"),
        _Node(1, ["common"], "/body/div[1]"),
        _Node(2, ["other"], "/body/div[2]"),
    ]
    target = _Node(0, ["rare", "common"], "/body/div[0]")
    index = _InMemoryIndex.build(sources, max_neighbors=1, max_token_appearance=10)

    neighbors = index.find_neighbors([target])[target]

    # Source 1 only shares the lower-IDF common token, while source 0 also
    # shares rare. The pinned implementation sorts ascending and keeps source 1.
    assert list(neighbors) == [sources[1]]


def test_parent_token_uses_kotlin_null_text_for_empty_parent_tokens() -> None:
    parent = _Node(0, [], "/body")
    child = _Node(1, ["button"], "/body/button[0]", parent=parent)

    _add_parent_tokens([parent, child], {})

    assert "#C_null" in child.tokens
    assert "#C_None" not in child.tokens


def test_sftm_runs_entirely_in_python_and_maps_page_xpath(tmp_path: Path) -> None:
    pair = _pair(
        tmp_path,
        '<html><body><button id="save">Old</button></body></html>',
        '<html><body><button id="save">New</button></body></html>',
    )
    matcher = SftmMatcher()

    matcher.prepare(pair)

    assert matcher.match(10).top1 == 20
    assert matcher.match(999).status == "missing_old_node"


def test_sftm_falls_back_to_dom_metadata_when_html_is_missing(tmp_path: Path) -> None:
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()

    old_body = DomNode(
        list_index=0,
        node_id=1,
        element_id=1,
        parent_id=-1,
        element_type=2,
        tag="body",
        text="",
        xpath="/html/body[1]",
        attributes={},
        bbox=BoundingBox(),
    )
    old_button = DomNode(
        list_index=1,
        node_id=10,
        element_id=10,
        parent_id=1,
        element_type=2,
        tag="button",
        text="Save",
        xpath="/html/body[1]/button[1]",
        attributes={"id": "save"},
        bbox=BoundingBox(),
    )
    new_body = DomNode(
        list_index=0,
        node_id=2,
        element_id=2,
        parent_id=-1,
        element_type=2,
        tag="body",
        text="",
        xpath="/html/body[1]",
        attributes={},
        bbox=BoundingBox(),
    )
    new_button = DomNode(
        list_index=1,
        node_id=20,
        element_id=20,
        parent_id=2,
        element_type=2,
        tag="button",
        text="Save",
        xpath="/html/body[1]/button[1]",
        attributes={"id": "save"},
        bbox=BoundingBox(),
    )
    old = PageSnapshot("site", "old", old_root, [old_body, old_button], [], None, None)
    new = PageSnapshot("site", "new", new_root, [new_body, new_button], [], None, None)
    pair = PagePair("site", tmp_path, old, new, {10: 20}, [], [])
    matcher = SftmMatcher()

    matcher.prepare(pair)

    assert matcher.input_mode == "dom_metadata"
    assert matcher.match(10).top1 == 20


def test_snapshot_parser_uses_zero_based_author_xpath() -> None:
    page = PageSnapshot(
        "site",
        "old",
        Path("."),
        [
            DomNode(0, 1, 1, -1, 2, "body", "", "/html/body[1]", {}, bbox=BoundingBox()),
            DomNode(
                1,
                10,
                10,
                1,
                2,
                "button",
                "Save",
                "/html/body[1]/button[2]",
                {"id": "save"},
                bbox=BoundingBox(),
            ),
        ],
        [],
        None,
        None,
    )

    nodes = _parse_snapshot(page, SftmParameters())

    assert [node.xpath for node in nodes] == ["/body", "/body/button[1]"]
    assert "id:save" in nodes[1].tokens
