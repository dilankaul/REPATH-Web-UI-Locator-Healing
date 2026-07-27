"""Cross-site and repeat aggregation."""

import pandas as pd


def aggregate_summary(site_results: pd.DataFrame) -> pd.DataFrame:
    records: list[dict] = []
    runtime_enabled = "runtime_total_ms" in site_results.columns

    for algorithm, group in site_results.groupby("algorithm", sort=False):
        first_repeat = int(group["repeat"].min())
        accuracy_group = group[group["repeat"] == first_repeat]
        total = int(accuracy_group["framework_queries"].sum())
        correct = int(accuracy_group["correct_top1"].sum())
        record = {
            "algorithm": algorithm,
            "framework_queries": total,
            "correct_top1": correct,
            "top1_accuracy": correct / total if total else 0.0,
            "repeats": int(group["repeat"].nunique()),
        }

        if runtime_enabled:
            runtime_samples = int(group["runtime_samples"].sum())
            runtime_total_ms = float(group["runtime_total_ms"].sum())
            record.update(
                {
                    "runtime_samples": runtime_samples,
                    "mean_runtime_ms": (
                        runtime_total_ms / runtime_samples
                        if runtime_samples
                        else 0.0
                    ),
                }
            )
        records.append(record)

    return pd.DataFrame(records)
