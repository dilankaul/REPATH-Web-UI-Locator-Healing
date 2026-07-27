from pathlib import Path

from repath_evaluation.domain.models import BoundingBox, DomNode, PagePair, PageSnapshot
from repath_evaluation.evaluation.protocol import build_queries


def _node(node_id: int, element_type: int = 2) -> DomNode:
    return DomNode(
        list_index=node_id,
        node_id=node_id,
        element_id=node_id,
        parent_id=-1,
        element_type=element_type,
        tag="button",
        text="",
        xpath=f"/html/body/button[{node_id + 1}]",
        bbox=BoundingBox(),
    )


def test_protocol_uses_only_match_map_and_excludes_group_nodes() -> None:
    old = PageSnapshot("site", "old", Path("."), [_node(1), _node(2, 1)], [], None, None)
    new = PageSnapshot("site", "new", Path("."), [_node(10), _node(20)], [], None, None)
    pair = PagePair(
        "site",
        Path("."),
        old,
        new,
        match_map={1: 10, 2: 20, 999: 10},
        add_list=[20],
        delete_list=[1],
    )

    queries = build_queries(pair)

    assert [(query.old_element_id, query.eligible) for query in queries] == [
        (1, True),
        (2, False),
        (999, False),
    ]
    assert len(queries) == len(pair.match_map)

