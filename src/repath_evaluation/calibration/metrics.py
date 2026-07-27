"""Confidence-margin metrics for REPATH candidate-score outputs."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


REQUIRED_SCORE_COLUMNS = frozenset({"qid", "label", "score"})


def normalise_scores(scored: pd.DataFrame, *, name: str) -> pd.DataFrame:
    """Validate and normalize a candidate-score frame."""
    missing = REQUIRED_SCORE_COLUMNS - set(scored.columns)
    if missing:
        raise ValueError(f"{name} scores missing columns: {sorted(missing)}")

    frame = scored.copy()
    frame["qid"] = frame["qid"].astype(str)
    frame["label"] = pd.to_numeric(frame["label"], errors="raise").astype(int)
    frame["score"] = pd.to_numeric(frame["score"], errors="raise").astype(float)

    positive_counts = frame.groupby("qid", sort=False)["label"].sum()
    if not positive_counts.eq(1).all():
        examples = positive_counts[~positive_counts.eq(1)].head().to_dict()
        raise ValueError(
            f"{name}: each retrievable query must have exactly one positive; "
            f"examples: {examples}"
        )
    return frame


def score_margin_table(scored: pd.DataFrame) -> pd.DataFrame:
    """Return Top-1, Top-2, correctness, and score margin per query."""
    ranked = scored[["qid", "label", "score"]].copy()
    ranked = ranked.sort_values(
        ["qid", "score"],
        ascending=[True, False],
        kind="mergesort",
    )
    ranked["rank"] = ranked.groupby("qid", sort=False).cumcount() + 1

    top1 = ranked[ranked["rank"] == 1][["qid", "label", "score"]].rename(
        columns={"label": "top1_correct", "score": "s1"}
    )
    top2 = ranked[ranked["rank"] == 2][["qid", "score"]].rename(
        columns={"score": "s2"}
    )
    margins = top1.merge(top2, on="qid", how="left")
    margins["s2"] = margins["s2"].fillna(margins["s1"])
    margins["margin"] = margins["s1"] - margins["s2"]
    margins["top1_correct"] = margins["top1_correct"].astype(int)
    return margins


def _metric_row(
    margins: pd.DataFrame,
    *,
    framework_queries: int,
    tau: float,
) -> dict[str, float | int]:
    accepted = margins[margins["margin"] >= float(tau)]
    accepted_count = int(len(accepted))
    correct = int(accepted["top1_correct"].sum())
    retrievable_queries = int(len(margins))

    precision = float(accepted["top1_correct"].mean()) if accepted_count else 1.0
    conditional_coverage = (
        accepted_count / retrievable_queries if retrievable_queries else 0.0
    )
    end_to_end_coverage = (
        accepted_count / framework_queries if framework_queries else 0.0
    )
    conditional_recall = correct / retrievable_queries if retrievable_queries else 0.0
    end_to_end_recall = correct / framework_queries if framework_queries else 0.0
    conditional_f1 = (
        2.0 * precision * conditional_recall / (precision + conditional_recall)
        if precision + conditional_recall
        else 0.0
    )
    end_to_end_f1 = (
        2.0 * precision * end_to_end_recall / (precision + end_to_end_recall)
        if precision + end_to_end_recall
        else 0.0
    )

    return {
        "tau_margin": float(tau),
        "accepted": accepted_count,
        "correct": correct,
        "framework_queries": int(framework_queries),
        "retrievable_queries": retrievable_queries,
        "retrieval_failures": int(framework_queries - retrievable_queries),
        "candidate_recall": (
            retrievable_queries / framework_queries if framework_queries else 0.0
        ),
        "precision": precision,
        "conditional_coverage": conditional_coverage,
        "end_to_end_coverage": end_to_end_coverage,
        "conditional_recall": conditional_recall,
        "end_to_end_recall": end_to_end_recall,
        "conditional_f1": conditional_f1,
        "end_to_end_f1": end_to_end_f1,
    }


def tau_curve(
    scored: pd.DataFrame,
    *,
    framework_queries: int,
    taus: Iterable[float],
) -> pd.DataFrame:
    """Evaluate confidence-margin metrics at every supplied threshold."""
    margins = score_margin_table(scored)
    return pd.DataFrame(
        [
            _metric_row(
                margins,
                framework_queries=framework_queries,
                tau=float(tau),
            )
            for tau in taus
        ]
    )


def evaluate_tau(
    scored: pd.DataFrame,
    *,
    framework_queries: int,
    tau: float,
    name: str,
) -> tuple[dict[str, float | int | str], pd.DataFrame]:
    """Evaluate one threshold and return aggregate and query-level decisions."""
    margins = score_margin_table(scored)
    result: dict[str, float | int | str] = _metric_row(
        margins,
        framework_queries=framework_queries,
        tau=tau,
    )
    result["name"] = name

    decisions = margins.copy()
    decisions["tau_margin"] = float(tau)
    decisions["accepted"] = decisions["margin"] >= float(tau)
    decisions["correct_accepted"] = (
        decisions["accepted"] & decisions["top1_correct"].astype(bool)
    )
    return result, decisions


def select_tau(
    curve: pd.DataFrame,
    *,
    target_precision: float,
    minimum_end_to_end_coverage: float,
) -> tuple[float, bool]:
    """Select the highest-coverage feasible development OOF threshold."""
    eligible = curve[
        (curve["precision"] >= float(target_precision))
        & (curve["end_to_end_coverage"] >= float(minimum_end_to_end_coverage))
    ].copy()
    precision_constraint_met = not eligible.empty

    if eligible.empty:
        eligible = curve[
            curve["end_to_end_coverage"] >= float(minimum_end_to_end_coverage)
        ].copy()
    if eligible.empty:
        raise ValueError(
            "No threshold satisfies the minimum end-to-end coverage "
            f"{minimum_end_to_end_coverage:.6f}"
        )

    if precision_constraint_met:
        ordering = ["end_to_end_coverage", "precision", "end_to_end_f1"]
    else:
        ordering = ["precision", "end_to_end_coverage", "end_to_end_f1"]

    chosen = eligible.sort_values(
        ordering,
        ascending=[False, False, False],
        kind="mergesort",
    ).iloc[0]
    return float(chosen["tau_margin"]), precision_constraint_met
