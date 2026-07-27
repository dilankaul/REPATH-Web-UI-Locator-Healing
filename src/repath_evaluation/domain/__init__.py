"""Framework-independent benchmark domain models."""

from .models import (
    BoundingBox,
    DomNode,
    MatchQuery,
    MatchResult,
    PagePair,
    PageSnapshot,
    PreDomNode,
    ScoredCandidate,
)

__all__ = ["BoundingBox", "DomNode", "MatchQuery", "MatchResult", "PagePair", "PageSnapshot", "PreDomNode", "ScoredCandidate"]
