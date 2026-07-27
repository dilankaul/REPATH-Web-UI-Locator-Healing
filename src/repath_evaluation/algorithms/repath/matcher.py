from __future__ import annotations

import time
from pathlib import Path

from ...domain.models import MatchResult, PagePair, ScoredCandidate
from ..base import ElementMatcher
from .runtime import RepathRuntime


class RepathMatcher(ElementMatcher):
    """Direct in-process REPATH matcher."""

    def __init__(
        self,
        model_path: Path,
        config_path: Path,
        device: str = "cpu",
        cache_models: bool = True,
        local_files_only: bool = False,
    ) -> None:
        self.runtime = RepathRuntime(
            model_path=model_path,
            config_path=config_path,
            device=device,
            cache_models=cache_models,
            local_files_only=local_files_only,
        )

    @property
    def name(self) -> str:
        return "REPATH"

    def prepare(self, page_pair: PagePair) -> None:
        super().prepare(page_pair)
        self.runtime.prepare(page_pair)

    def match(self, old_node_id: int) -> MatchResult:
        start_ns = time.perf_counter_ns()
        try:
            ranking = self.runtime.rank(old_node_id)
        except Exception as exc:  # noqa: BLE001
            return MatchResult(
                ranking=(),
                query_time_ns=time.perf_counter_ns() - start_ns,
                status="algorithm_error",
                details=str(exc),
            )

        scored_candidates = tuple(
            ScoredCandidate(
                node_id=int(node_id),
                score=float(score),
            )
            for node_id, score in ranking
        )
        return MatchResult(
            ranking=scored_candidates,
            query_time_ns=time.perf_counter_ns() - start_ns,
            status="ok" if scored_candidates else "no_prediction",
        )
