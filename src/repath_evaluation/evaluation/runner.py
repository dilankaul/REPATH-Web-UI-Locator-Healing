from __future__ import annotations

import gc
import statistics
import time
from collections.abc import Callable
from pathlib import Path

from ..algorithms.base import ElementMatcher
from ..data.loader import load_page_pair
from ..domain.models import MatchResult
from .protocol import build_queries


def _row(
    *,
    algorithm: str,
    site: str,
    repeat: int,
    old_element_id: int,
    expected_new_element_id: int,
    result: MatchResult | None,
    error: Exception | None = None,
    runtime_ns: int | None = None,
) -> dict:
    predicted = result.top1 if result is not None else None
    row = {
        "algorithm": algorithm,
        "site": site,
        "repeat": repeat,
        "old_element_id": old_element_id,
        "expected_new_element_id": expected_new_element_id,
        "predicted_new_element_id": predicted,
        "correct": predicted == expected_new_element_id,
        "status": result.status if result is not None else "algorithm_error",
        "details": result.details if result is not None else str(error or "unknown error"),
    }
    if runtime_ns is not None:
        row["runtime_ms"] = runtime_ns / 1_000_000
    return row


def _accuracy_summary(algorithm: str, site: str, repeat: int, rows: list[dict]) -> dict:
    correct = sum(bool(row["correct"]) for row in rows)
    total = len(rows)
    return {
        "algorithm": algorithm,
        "site": site,
        "repeat": repeat,
        "framework_queries": total,
        "correct_top1": correct,
        "top1_accuracy": correct / total if total else 0.0,
        "no_prediction": sum(row["predicted_new_element_id"] is None for row in rows),
    }


def _run_fast(
    site_path: Path,
    matcher_factory: Callable[[], ElementMatcher],
    repeat: int,
) -> tuple[list[dict], dict]:
    pair = load_page_pair(site_path)
    queries = [query for query in build_queries(pair) if query.eligible]
    matcher = matcher_factory()
    rows: list[dict] = []
    try:
        matcher.prepare(pair)
        for query in queries:
            try:
                result = matcher.match(query.old_element_id)
                error = None
            except Exception as exc:  # noqa: BLE001
                result = None
                error = exc
            rows.append(
                _row(
                    algorithm=matcher.name,
                    site=pair.site,
                    repeat=repeat,
                    old_element_id=query.old_element_id,
                    expected_new_element_id=query.expected_new_element_id,
                    result=result,
                    error=error,
                )
            )
    finally:
        matcher.close()

    return rows, _accuracy_summary(matcher.name, pair.site, repeat, rows)


def _run_end_to_end(
    site_path: Path,
    matcher_factory: Callable[[], ElementMatcher],
    repeat: int,
    algorithm_name: str | None,
) -> tuple[list[dict], dict]:
    # Load once only to enumerate the fixed eligible queries. This discovery
    # work is not part of any individual query execution.
    reference_pair = load_page_pair(site_path)
    queries = [query for query in build_queries(reference_pair) if query.eligible]

    if algorithm_name is None:
        # Direct library callers may not know the matcher's display name.
        probe = matcher_factory()
        algorithm = probe.name
        probe.close()
        del probe
        gc.collect()
    else:
        algorithm = algorithm_name

    rows: list[dict] = []
    runtime_values: list[int] = []
    for query in queries:
        matcher: ElementMatcher | None = None
        result: MatchResult | None = None
        error: Exception | None = None
        start_ns = time.perf_counter_ns()
        try:
            pair = load_page_pair(site_path)
            matcher = matcher_factory()
            matcher.prepare(pair)
            result = matcher.match(query.old_element_id)
        except Exception as exc:  # noqa: BLE001
            error = exc
        finally:
            if matcher is not None:
                matcher.close()
            runtime_ns = time.perf_counter_ns() - start_ns

        runtime_values.append(runtime_ns)
        rows.append(
            _row(
                algorithm=algorithm,
                site=reference_pair.site,
                repeat=repeat,
                old_element_id=query.old_element_id,
                expected_new_element_id=query.expected_new_element_id,
                result=result,
                error=error,
                runtime_ns=runtime_ns,
            )
        )
        del matcher, result
        gc.collect()

    summary = _accuracy_summary(algorithm, reference_pair.site, repeat, rows)
    total_runtime_ns = sum(runtime_values)
    summary.update(
        {
            "runtime_samples": len(runtime_values),
            "runtime_total_ms": total_runtime_ns / 1_000_000,
            "mean_runtime_ms": (
                statistics.fmean(runtime_values) / 1_000_000
                if runtime_values
                else 0.0
            ),
        }
    )
    return rows, summary


def run_site(
    site_path: Path,
    matcher_factory: Callable[[], ElementMatcher],
    repeat: int,
    *,
    measure_runtime: bool = False,
    algorithm_name: str | None = None,
) -> tuple[list[dict], dict]:
    if measure_runtime:
        return _run_end_to_end(
            site_path,
            matcher_factory,
            repeat,
            algorithm_name,
        )
    return _run_fast(site_path, matcher_factory, repeat)
