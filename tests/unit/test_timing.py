from pathlib import Path

import repath_evaluation.evaluation.runner as evaluator
from repath_evaluation.algorithms.base import ElementMatcher
from repath_evaluation.domain.models import (
    BoundingBox,
    DomNode,
    MatchResult,
    PagePair,
    PageSnapshot,
    ScoredCandidate,
)


def _pair(tmp_path: Path) -> PagePair:
    old_node = DomNode(0, 1, 1, -1, 2, "button", "", "/old", bbox=BoundingBox())
    new_node = DomNode(0, 2, 2, -1, 2, "button", "", "/new", bbox=BoundingBox())
    return PagePair(
        "site",
        tmp_path,
        PageSnapshot("site", "old", Path("."), [old_node], [], None, None),
        PageSnapshot("site", "new", Path("."), [new_node], [], None, None),
        {1: 2},
        [],
        [],
    )


class _TimedMatcher(ElementMatcher):
    constructed = 0
    prepared = 0

    def __init__(self) -> None:
        type(self).constructed += 1

    @property
    def name(self) -> str:
        return "timed"

    def prepare(self, page_pair: PagePair) -> None:
        super().prepare(page_pair)
        type(self).prepared += 1

    def match(self, old_node_id: int) -> MatchResult:
        return MatchResult((ScoredCandidate(2, 1.0),), 3_000_000)


def test_default_fast_mode_omits_runtime_results(monkeypatch, tmp_path) -> None:
    pair = _pair(tmp_path)
    monkeypatch.setattr(evaluator, "load_page_pair", lambda _: pair)
    _TimedMatcher.constructed = 0
    _TimedMatcher.prepared = 0

    rows, summary = evaluator.run_site(tmp_path, _TimedMatcher, repeat=1)

    assert rows[0]["correct"] is True
    assert "runtime_ms" not in rows[0]
    assert "mean_runtime_ms" not in summary
    assert _TimedMatcher.constructed == 1
    assert _TimedMatcher.prepared == 1


def test_measure_runtime_rebuilds_each_query_and_reports_end_to_end_mean(
    monkeypatch,
    tmp_path,
) -> None:
    pair = _pair(tmp_path)
    loads = 0

    def load_pair(_):
        nonlocal loads
        loads += 1
        return pair

    clock = iter([1_000, 6_001_000])
    monkeypatch.setattr(evaluator, "load_page_pair", load_pair)
    monkeypatch.setattr(evaluator.time, "perf_counter_ns", lambda: next(clock))
    monkeypatch.setattr(evaluator.gc, "collect", lambda: 0)
    _TimedMatcher.constructed = 0
    _TimedMatcher.prepared = 0

    rows, summary = evaluator.run_site(
        tmp_path,
        _TimedMatcher,
        repeat=1,
        measure_runtime=True,
    )

    assert rows[0]["correct"] is True
    assert rows[0]["runtime_ms"] == 6.0
    assert summary["mean_runtime_ms"] == 6.0
    assert summary["runtime_samples"] == 1
    assert loads == 2  # query discovery plus the independent timed execution
    assert _TimedMatcher.constructed == 2  # untimed probe plus timed execution
    assert _TimedMatcher.prepared == 1
