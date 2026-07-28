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


def _pair(tmp_path: Path, *, query_count: int = 1) -> PagePair:
    old_nodes = [
        DomNode(0, 1, 1, -1, 2, "button", "", "/old-1", bbox=BoundingBox())
    ]
    new_nodes = [
        DomNode(0, 2, 2, -1, 2, "button", "", "/new-2", bbox=BoundingBox())
    ]
    match_map = {1: 2}
    if query_count == 2:
        old_nodes.append(
            DomNode(1, 3, 3, -1, 2, "button", "", "/old-3", bbox=BoundingBox())
        )
        new_nodes.append(
            DomNode(1, 4, 4, -1, 2, "button", "", "/new-4", bbox=BoundingBox())
        )
        match_map[3] = 4

    return PagePair(
        "site",
        tmp_path,
        PageSnapshot("site", "old", Path("."), old_nodes, [], None, None),
        PageSnapshot("site", "new", Path("."), new_nodes, [], None, None),
        match_map,
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
        target = 2 if old_node_id == 1 else 4
        return MatchResult((ScoredCandidate(target, 1.0),), 3_000_000)


def test_default_fast_mode_omits_runtime_results(monkeypatch, tmp_path) -> None:
    pair = _pair(tmp_path)
    monkeypatch.setattr(evaluator, "load_page_pair", lambda _: pair)
    _TimedMatcher.constructed = 0
    _TimedMatcher.prepared = 0

    rows, summary = evaluator.run_site(tmp_path, _TimedMatcher, repeat=1)

    assert rows[0]["correct"] is True
    assert "runtime_mode" not in rows[0]
    assert "runtime_ms" not in rows[0]
    assert "mean_runtime_ms" not in summary
    assert _TimedMatcher.constructed == 1
    assert _TimedMatcher.prepared == 1


def test_cold_runtime_rebuilds_each_query_and_reports_independent_mean(
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
        runtime_mode="cold",
    )

    assert rows[0]["correct"] is True
    assert rows[0]["runtime_mode"] == "cold"
    assert rows[0]["runtime_ms"] == 6.0
    assert summary["runtime_mode"] == "cold"
    assert summary["mean_runtime_ms"] == 6.0
    assert summary["runtime_samples"] == 1
    assert loads == 2
    assert _TimedMatcher.constructed == 2
    assert _TimedMatcher.prepared == 1


def test_amortized_runtime_prepares_once_and_divides_page_pair_total(
    monkeypatch,
    tmp_path,
) -> None:
    pair = _pair(tmp_path, query_count=2)
    loads = 0

    def load_pair(_):
        nonlocal loads
        loads += 1
        return pair

    clock = iter([1_000, 12_001_000])
    monkeypatch.setattr(evaluator, "load_page_pair", load_pair)
    monkeypatch.setattr(evaluator.time, "perf_counter_ns", lambda: next(clock))
    _TimedMatcher.constructed = 0
    _TimedMatcher.prepared = 0

    rows, summary = evaluator.run_site(
        tmp_path,
        _TimedMatcher,
        repeat=1,
        runtime_mode="amortized",
    )

    assert [row["correct"] for row in rows] == [True, True]
    assert [row["runtime_mode"] for row in rows] == ["amortized", "amortized"]
    assert [row["runtime_ms"] for row in rows] == [6.0, 6.0]
    assert summary["runtime_mode"] == "amortized"
    assert summary["runtime_total_ms"] == 12.0
    assert summary["runtime_samples"] == 2
    assert summary["mean_runtime_ms"] == 6.0
    assert loads == 2
    assert _TimedMatcher.constructed == 1
    assert _TimedMatcher.prepared == 1
