from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from repath_evaluation.calibration import run_calibration
from repath_evaluation.calibration.metrics import (
    evaluate_tau,
    normalise_scores,
    score_margin_table,
    select_tau,
    tau_curve,
)


def _development_scores() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"qid": "d1", "label": 1, "score": 1.0},
            {"qid": "d1", "label": 0, "score": 0.1},
            {"qid": "d2", "label": 1, "score": 0.9},
            {"qid": "d2", "label": 0, "score": 0.59},
            {"qid": "d3", "label": 0, "score": 0.8},
            {"qid": "d3", "label": 1, "score": 0.7},
        ]
    )


def _test_scores() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"qid": "t1", "label": 1, "score": 0.9},
            {"qid": "t1", "label": 0, "score": 0.2},
            {"qid": "t2", "label": 0, "score": 0.8},
            {"qid": "t2", "label": 1, "score": 0.4},
        ]
    )


def test_score_margin_table_uses_stable_top1_and_top2() -> None:
    scores = normalise_scores(_development_scores(), name="development")
    margins = score_margin_table(scores).set_index("qid")

    assert margins.loc["d1", "margin"] == pytest.approx(0.9)
    assert margins.loc["d2", "margin"] == pytest.approx(0.31)
    assert margins.loc["d3", "top1_correct"] == 0


def test_manual_tau_reports_precision_coverage_recall_and_f1() -> None:
    scores = normalise_scores(_development_scores(), name="development")
    result, decisions = evaluate_tau(
        scores,
        framework_queries=4,
        tau=0.2,
        name="development",
    )

    assert result["accepted"] == 2
    assert result["correct"] == 2
    assert result["precision"] == 1.0
    assert result["conditional_coverage"] == pytest.approx(2 / 3)
    assert result["end_to_end_coverage"] == 0.5
    assert result["conditional_recall"] == pytest.approx(2 / 3)
    assert result["end_to_end_recall"] == 0.5
    assert result["conditional_f1"] == pytest.approx(0.8)
    assert result["end_to_end_f1"] == pytest.approx(2 / 3)
    assert decisions["accepted"].sum() == 2


def test_auto_selection_maximises_coverage_subject_to_constraints() -> None:
    scores = normalise_scores(_development_scores(), name="development")
    curve = tau_curve(
        scores,
        framework_queries=4,
        taus=[0.0, 0.2, 0.4],
    )
    tau, met = select_tau(
        curve,
        target_precision=1.0,
        minimum_end_to_end_coverage=0.5,
    )

    assert met is True
    assert tau == 0.2


def test_file_workflow_writes_manual_and_auto_outputs(tmp_path: Path) -> None:
    manifest = pd.DataFrame(
        [
            {"qid": "d1", "site": "dev", "split": "development"},
            {"qid": "d2", "site": "dev", "split": "development"},
            {"qid": "d3", "site": "dev", "split": "development"},
            {"qid": "d4", "site": "dev", "split": "development"},
            {"qid": "t1", "site": "test", "split": "test"},
            {"qid": "t2", "site": "test", "split": "test"},
        ]
    )
    manifest_path = tmp_path / "manifest.csv"
    development_path = tmp_path / "development.csv"
    test_path = tmp_path / "test.csv"
    manifest.to_csv(manifest_path, index=False)
    _development_scores().to_csv(development_path, index=False)
    _test_scores().to_csv(test_path, index=False)

    manual_output = tmp_path / "manual"
    summary, curve, decisions = run_calibration(
        manifest_path=manifest_path,
        development_scores_path=development_path,
        test_scores_path=test_path,
        output_dir=manual_output,
        tau=0.2,
    )
    assert curve is None
    assert len(summary) == 2
    assert set(decisions["split"]) == {"development", "test"}
    assert (manual_output / "tau_margin_summary.csv").is_file()
    assert not (manual_output / "tau_margin_development_oof_curve.csv").exists()

    auto_output = tmp_path / "auto"
    summary, curve, _ = run_calibration(
        manifest_path=manifest_path,
        development_scores_path=development_path,
        test_scores_path=test_path,
        output_dir=auto_output,
        target_precision=1.0,
        minimum_end_to_end_coverage=0.5,
        tau_min=0.0,
        tau_max=0.4,
        tau_step=0.2,
    )
    assert float(summary.iloc[0]["tau_margin"]) == 0.2
    assert curve is not None and len(curve) == 3
    metadata = json.loads((auto_output / "calibration_metadata.json").read_text())
    assert metadata["selection_mode"] == "development_oof_auto"
    assert metadata["precision_constraint_met"] is True
