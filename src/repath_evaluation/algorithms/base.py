from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.models import MatchResult, PagePair


class ElementMatcher(ABC):
    pair: PagePair

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    def prepare(self, page_pair: PagePair) -> None:
        self.pair = page_pair

    @abstractmethod
    def match(self, old_node_id: int) -> MatchResult:
        raise NotImplementedError

    def close(self) -> None:
        return None
