from __future__ import annotations

import gc
import time
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from ..algorithms.base import ElementMatcher
from ..data.loader import load_page_pair
from ..domain.models import MatchResult
from .protocol import build_queries

RuntimeMode = Literal["cold", "amortized"]


def _row(
    *,
    algorithm: str,
    site: str,
    repeat: int,
    old_element_id: int,
    expected_new_element_id: int,
    result: MatchResult | None,
    error: Exception | None = None,
    runtime_mode: RuntimeMode | None = None,
    runtime_ns: int | float | None = None,
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
    if runtime_mode is not None:
        row["runtime_mode"] = runtime_mode
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


def _runtime_summary(
    algorithm: str,
    site: str,
    repeat: int,
    rows: list[dict],
    runtime_mode: RuntimeMode,
    total_runtime_ns: int,
) -> dict:
    summary = _accuracy_summary(algorithm, site, repeat, rows)
    runtime_samples = len(rows)
    summary.update(
        {
            "runtime_mode": runtime_mode,
            "runtime_samples": runtime_samples,
            "runtime_total_ms": total_runtime_ns / 1_000_000,
            "mean_runtime_ms": (
                total_runtime_ns / runtime_samples / 1_000_000
                if runtime_samples
                else 0.0
            ),
        }
    )
    return summary


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


def _run_cold(
    site_path: Path,
    matcher_factory: Callable[[], ElementMatcher],
    repeat: int,
    algorithm_name: str | None,
) -> tuple[list[dict], dict]:
    # Query discovery is intentionally outside each independent timed execution.
    reference_pair = load_page_pair(site_path)
    queries = [query for query in build_queries(reference_pair) if query.eligible]

    if algorithm_name is None:
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
                runtime_mode="cold",
                runtime_ns=runtime_ns,
            )
        )
        del matcher, result
        gc.collect()

    return rows, _runtime_summary(
        algorithm,
        reference_pair.site,
        repeat,
        rows,
        "cold",
        sum(runtime_values),
    )


def _run_amortized(
    site_path: Path,
    matcher_factory: Callable[[], ElementMatcher],
    repeat: int,
    algorithm_name: str | None,
) -> tuple[list[dict], dict]:
    reference_pair = load_page_pair(site_path)
    queries = [query for query in build_queries(reference_pair) if query.eligible]
    matcher = matcher_factory()
    algorithm = algorithm_name or matcher.name

    outcomes: list[tuple[MatchResult | None, Exception | None]] = []
    preparation_error: Exception | None = None
    start_ns = time.perf_counter_ns()
    try:
        pair = load_page_pair(site_path)
        matcher.prepare(pair)
        for query in queries:
            try:
                outcomes.append((matcher.match(query.old_element_id), None))
            except Exception as exc:  # noqa: BLE001
                outcomes.append((None, exc))
    except Exception as exc:  # noqa: BLE001
        preparation_error = exc
    finally:
        matcher.close()
        total_runtime_ns = time.perf_counter_ns() - start_ns

    if preparation_error is not None:
        outcomes = [(None, preparation_error) for _ in queries]

    amortized_runtime_ns = (
        total_runtime_ns / len(queries)
        if queries
        else 0.0
    )
    rows = [
        _row(
            algorithm=algorithm,
            site=reference_pair.site,
            repeat=repeat,
            old_element_id=query.old_element_id,
            expected_new_element_id=query.expected_new_element_id,
            result=result,
            error=error,
            runtime_mode="amortized",
            runtime_ns=amortized_runtime_ns,
        )
        for query, (result, error) in zip(queries, outcomes, strict=True)
    ]

    return rows, _runtime_summary(
        algorithm,
        reference_pair.site,
        repeat,
        rows,
        "amortized",
        total_runtime_ns,
    )


def run_site(
    site_path: Path,
    matcher_factory: Callable[[], ElementMatcher],
    repeat: int,
    *,
    runtime_mode: RuntimeMode | None = None,
    algorithm_name: str | None = None,
) -> tuple[list[dict], dict]:
    if runtime_mode == "cold":
        return _run_cold(site_path, matcher_factory, repeat, algorithm_name)
    if runtime_mode == "amortized":
        return _run_amortized(site_path, matcher_factory, repeat, algorithm_name)
    if runtime_mode is not None:
        raise ValueError(f"Unknown runtime mode: {runtime_mode}")
    return _run_fast(site_path, matcher_factory, repeat)
