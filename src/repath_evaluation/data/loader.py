"""Load UITestFix page pairs into the benchmark domain model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..domain.models import BoundingBox, DomNode, PagePair, PageSnapshot, PreDomNode


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _first(mapping: dict[str, Any], *names: str, default: Any = None) -> Any:
    return next(
        (mapping[name] for name in names if name in mapping and mapping[name] is not None), default
    )


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _boolean(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    return (
        value.casefold() not in {"", "0", "false", "no", "none"}
        if isinstance(value, str)
        else bool(value)
    )


def _attributes(raw: dict[str, Any]) -> dict[str, str]:
    value = _first(raw, "attributes", "attrs", "attributeMap", default={})
    if isinstance(value, dict):
        return {str(key): "" if item is None else str(item) for key, item in value.items()}
    if isinstance(value, list):
        return {
            str(_first(item, "name", "key")): str(_first(item, "value", default=""))
            for item in value
            if isinstance(item, dict) and _first(item, "name", "key") is not None
        }
    return {}


def _bbox(raw: dict[str, Any]) -> BoundingBox:
    box = _first(raw, "boundingBox", "bbox", "rect", default={})
    box = box if isinstance(box, dict) else {}
    return BoundingBox(
        _integer(_first(raw, "x", "left", default=_first(box, "x", "left", default=0))),
        _integer(_first(raw, "y", "top", default=_first(box, "y", "top", default=0))),
        _integer(_first(raw, "width", default=_first(box, "width", default=0))),
        _integer(_first(raw, "height", default=_first(box, "height", default=0))),
    )


def _records(payload: Any, *containers: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for name in containers:
            if isinstance(payload.get(name), list):
                return [item for item in payload[name] if isinstance(item, dict)]
    return []


def load_dom_nodes(path: Path) -> list[DomNode]:
    nodes = []
    for index, raw in enumerate(_records(read_json(path), "domNodeInfoList", "nodes", "nodeList")):
        attrs = _attributes(raw)
        node_id = _integer(_first(raw, "nodeId", "newElementId", "oldElementId", default=index))
        parent = _first(raw, "parentId", "parentNodeId")
        children = _first(raw, "children", "childNodeIds", default=())
        children = children if isinstance(children, (list, tuple)) else ()
        nodes.append(
            DomNode(
                index,
                node_id,
                _integer(_first(raw, "elementId", default=node_id), node_id),
                None if parent is None else _integer(parent),
                _integer(_first(raw, "elementType", "type", default=0)),
                str(_first(raw, "tagName", "tag", default="")),
                str(_first(raw, "text", "textContent", default="")),
                str(_first(raw, "xpath", "xPath", default="")),
                attrs,
                tuple(_integer(child) for child in children),
                _boolean(_first(raw, "displayed", "isDisplayed", "visible")),
                _bbox(raw),
                str(_first(raw, "linkText", default="")),
                str(_first(raw, "id", default=attrs.get("id", ""))),
                str(_first(raw, "name", default=attrs.get("name", ""))),
                raw,
            )
        )
    return nodes


def load_pre_nodes(path: Path) -> list[PreDomNode]:
    nodes = []
    for index, raw in enumerate(
        _records(read_json(path), "preDomNodeInfoList", "nodes", "nodeList")
    ):
        attrs = _attributes(raw)
        element_id = _integer(_first(raw, "elementId", "nodeId", default=index))
        nodes.append(
            PreDomNode(
                index,
                element_id,
                _integer(
                    _first(
                        raw, "coreElementId", "newElementId", "oldElementId", default=element_id
                    ),
                    element_id,
                ),
                str(_first(raw, "tagName", "tag", default="")),
                str(_first(raw, "text", "textContent", default="")),
                str(_first(raw, "xpath", "xPath", default="")),
                attrs,
                _bbox(raw),
                _boolean(_first(raw, "displayed", "isDisplayed", "visible")),
                str(_first(raw, "id", default=attrs.get("id", ""))),
                str(_first(raw, "name", default=attrs.get("name", ""))),
                raw,
            )
        )
    return nodes


def _optional_file(root: Path, names: tuple[str, ...]) -> Path | None:
    return next((root / name for name in names if (root / name).is_file()), None)


def _snapshot(site: str, version: str, root: Path) -> PageSnapshot:
    dom = root / "domNodeInfo.json"
    if not dom.is_file():
        raise FileNotFoundError(f"Missing DOM data: {dom}")
    pre = _optional_file(root, ("preDomNodeInfo.json", "preDomNode.json"))
    return PageSnapshot(
        site,
        version,
        root,
        load_dom_nodes(dom),
        load_pre_nodes(pre) if pre else [],
        _optional_file(root, ("fullScreen.png", "fullScreenshot.png", "screenshot.png")),
        _optional_file(root, ("page.html", "index.html", "dom.html")),
    )


def load_page_pair(site_path: Path) -> PagePair:
    site_path = Path(site_path)
    result_path = site_path / "result" / "result.json"
    result = read_json(result_path)
    matches = _first(result, "matchMap", "matches", default={})
    if not isinstance(matches, dict):
        raise TypeError(f"Expected an object for matchMap in {result_path}")
    return PagePair(
        site_path.name,
        site_path,
        _snapshot(site_path.name, "old", site_path / "old"),
        _snapshot(site_path.name, "new", site_path / "new"),
        {_integer(old): _integer(new) for old, new in matches.items()},
        [_integer(item) for item in _first(result, "addList", default=[])],
        [_integer(item) for item in _first(result, "deleteList", default=[])],
    )


def discover_sites(data_root: Path) -> list[Path]:
    data_root = Path(data_root)
    if not data_root.is_dir():
        return []
    return sorted(
        (
            path
            for path in data_root.iterdir()
            if path.is_dir()
            and (path / "old" / "domNodeInfo.json").is_file()
            and (path / "new" / "domNodeInfo.json").is_file()
            and (path / "result" / "result.json").is_file()
        ),
        key=lambda path: path.name.casefold(),
    )
