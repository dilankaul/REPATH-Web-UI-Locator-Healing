import json

from repath_evaluation.data.loader import load_page_pair


def test_loader_accepts_alternative_fields_and_missing_optional_files(tmp_path) -> None:
    site = tmp_path / "site"
    (site / "old").mkdir(parents=True)
    (site / "new").mkdir()
    (site / "result").mkdir()

    old_nodes = {
        "nodes": [
            {
                "nodeId": 7,
                "elementId": 17,
                "elementType": 2,
                "tag": "button",
                "textContent": "Save",
                "xPath": "/html/body/button[1]",
                "attrs": {"ID": "save"},
            }
        ]
    }
    new_nodes = {
        "domNodeInfoList": [
            {
                "newElementId": 8,
                "elementId": 18,
                "elementType": 2,
                "tagName": "button",
                "text": "Save",
                "xpath": "/html/body/button[2]",
            }
        ]
    }
    (site / "old" / "domNodeInfo.json").write_text(json.dumps(old_nodes), encoding="utf-8")
    (site / "new" / "domNodeInfo.json").write_text(json.dumps(new_nodes), encoding="utf-8")
    (site / "result" / "result.json").write_text(
        json.dumps({"matchMap": {"7": 8}, "addList": [8], "deleteList": [7]}),
        encoding="utf-8",
    )

    pair = load_page_pair(site)

    assert pair.old_page.resolve_node(7).attr("id") == "save"
    assert pair.old_page.resolve_node(0).node_id == 7
    assert pair.old_page.pre_nodes == []
    assert pair.old_page.full_screen_path is None
    assert pair.match_map == {7: 8}
    assert pair.add_list == [8]
    assert pair.delete_list == [7]

