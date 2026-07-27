import pandas as pd

from repath_evaluation.evaluation.aggregation import aggregate_summary


def test_runtime_mean_is_weighted_across_all_query_executions() -> None:
    site_results = pd.DataFrame(
        [
            {
                "algorithm": "WATER",
                "site": "a",
                "repeat": 1,
                "framework_queries": 1,
                "correct_top1": 1,
                "runtime_samples": 1,
                "runtime_total_ms": 100.0,
            },
            {
                "algorithm": "WATER",
                "site": "b",
                "repeat": 1,
                "framework_queries": 3,
                "correct_top1": 2,
                "runtime_samples": 3,
                "runtime_total_ms": 600.0,
            },
        ]
    )

    summary = aggregate_summary(site_results)

    assert summary.loc[0, "framework_queries"] == 4
    assert summary.loc[0, "correct_top1"] == 3
    assert summary.loc[0, "top1_accuracy"] == 0.75
    assert summary.loc[0, "runtime_samples"] == 4
    assert summary.loc[0, "mean_runtime_ms"] == 175.0
