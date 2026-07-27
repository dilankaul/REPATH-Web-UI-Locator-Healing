from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BoundingBox:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

    def strictly_contains(self, px: float, py: float) -> bool:
        return self.x < px < self.x + self.width and self.y < py < self.y + self.height


@dataclass
class DomNode:
    list_index: int
    node_id: int
    element_id: int
    parent_id: int | None
    element_type: int
    tag: str
    text: str
    xpath: str
    attributes: dict[str, str] = field(default_factory=dict)
    children: tuple[int, ...] = ()
    displayed: bool = True
    bbox: BoundingBox = field(default_factory=BoundingBox)
    link_text: str = ""
    explicit_id: str = ""
    name: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def attr(self, name: str) -> str:
        direct = self.attributes.get(name)
        if direct is not None:
            return str(direct)
        lowered = name.casefold()
        for key, value in self.attributes.items():
            if str(key).casefold() == lowered:
                return "" if value is None else str(value)
        return ""

    def serializable(self) -> dict[str, Any]:
        return {
            "list_index": self.list_index,
            "node_id": self.node_id,
            "element_id": self.element_id,
            "parent_id": self.parent_id,
            "element_type": self.element_type,
            "tag": self.tag,
            "text": self.text,
            "xpath": self.xpath,
            "attributes": self.attributes,
            "children": list(self.children),
            "displayed": self.displayed,
            "x": self.bbox.x,
            "y": self.bbox.y,
            "width": self.bbox.width,
            "height": self.bbox.height,
            "link_text": self.link_text,
            "id": self.explicit_id,
            "name": self.name,
        }


@dataclass
class PreDomNode:
    list_index: int
    element_id: int
    core_element_id: int
    tag: str
    text: str
    xpath: str
    attributes: dict[str, str]
    bbox: BoundingBox
    displayed: bool
    explicit_id: str = ""
    name: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def attr(self, name: str) -> str:
        direct = self.attributes.get(name)
        if direct is not None:
            return str(direct)
        lowered = name.casefold()
        for key, value in self.attributes.items():
            if str(key).casefold() == lowered:
                return "" if value is None else str(value)
        return ""


@dataclass
class PageSnapshot:
    site: str
    version: str
    root: Path
    nodes: list[DomNode]
    pre_nodes: list[PreDomNode]
    full_screen_path: Path | None
    html_path: Path | None

    def __post_init__(self) -> None:
        self.nodes_by_id = {node.node_id: node for node in self.nodes}
        self.nodes_by_index = {node.list_index: node for node in self.nodes}
        self.pre_by_element_id = {node.element_id: node for node in self.pre_nodes}
        self.pre_by_index = {node.list_index: node for node in self.pre_nodes}

    def resolve_node(self, identifier: int) -> DomNode | None:
        return self.nodes_by_id.get(identifier) or self.nodes_by_index.get(identifier)

    def resolve_pre(self, identifier: int) -> PreDomNode | None:
        return self.pre_by_element_id.get(identifier) or self.pre_by_index.get(identifier)

    def grouped_node_by_xpath(self, xpath: str) -> DomNode | None:
        for node in self.nodes:
            if node.xpath == xpath:
                return node
        return None


@dataclass
class PagePair:
    site: str
    root: Path
    old_page: PageSnapshot
    new_page: PageSnapshot
    match_map: dict[int, int]
    add_list: list[int]
    delete_list: list[int]


@dataclass(frozen=True)
class MatchQuery:
    site: str
    old_element_id: int
    expected_new_element_id: int
    eligible: bool
    old_node_found: bool


@dataclass(frozen=True)
class ScoredCandidate:
    node_id: int
    score: float


@dataclass(frozen=True)
class MatchResult:
    ranking: tuple[ScoredCandidate, ...]
    query_time_ns: int
    status: str = "ok"
    details: str = ""

    @property
    def top1(self) -> int | None:
        return self.ranking[0].node_id if self.ranking else None
