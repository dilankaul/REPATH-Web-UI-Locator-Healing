"""File-based REPATH confidence-margin calibration workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .metrics import evaluate_tau, normalise_scores, select_tau, tau_curve


REQUIRED_MANIFEST_COLUMNS = frozenset({"qid", "site", "split"})


def _load_manifest(path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(path, keep_default_na=False)
    missing = REQUIRED_MANIFEST_COLUMNS - set(manifest.columns)
    if missing:
        raise ValueError(f"Manifest missing columns: {sorted(missing)}")
    manifest = manifest.copy()
    manifest["qid"] = manifest["qid"].astype(str)
    manifest["split"] = manifest["split"].astype(str).str.casefold()
    return manifest


def _validate_membership(
    *,
    manifest: pd.DataFrame,
    scores: pd.DataFrame,
    split: str,
) -> set[str]:
    framework_qids = set(manifest.loc[manifest["split"] == split, "qid"])
    score_qids = set(scores["qid"])
    unknown = score_qids - framework_qids
    if unknown:
        raise ValueError(
            f"{split} scores contain queries absent from the manifest; "
            f"examples: {sorted(unknown)[:5]}"
        )
    return framework_qids


def _write_runtime_config(
    *,
    base_config_path: Path,
    output_path: Path,
    tau: float,
    target_precision: float | None,
    minimum_end_to_end_coverage: float | None,
    precision_constraint_met: bool | None,
    development_result: dict[str, Any],
    test_result: dict[str, Any],
) -> None:
    config = joblib.load(base_config_path)
    if not isinstance(config, dict):
        raise TypeError("Base REPATH configuration must contain a dictionary")
    config = dict(config)
    config.update(
        {
            "tau_margin": float(tau),
            "target_precision": target_precision,
            "minimum_end_to_end_coverage": minimum_end_to_end_coverage,
            "precision_constraint_met": precision_constraint_met,
            "development_tau_metrics": development_result,
            "test_tau_metrics": test_result,
            "calibration_protocol": "pooled_four_fold_development_oof",
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(config, output_path)


def run_calibration(
    *,
    manifest_path: Path,
    development_scores_path: Path,
    test_scores_path: Path,
    output_dir: Path,
    tau: float | None = None,
    target_precision: float = 0.99,
    minimum_end_to_end_coverage: float = 0.80,
    tau_min: float = 0.0,
    tau_max: float = 1.0,
    tau_step: float = 0.05,
    base_config_path: Path | None = None,
    config_output_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame | None, pd.DataFrame]:
    """Run manual-threshold evaluation or development-OOF calibration."""
    if tau_step <= 0:
        raise ValueError("tau_step must be greater than zero")
    if tau_min > tau_max:
        raise ValueError("tau_min must not exceed tau_max")
    if not 0.0 <= target_precision <= 1.0:
        raise ValueError("target_precision must be between zero and one")
    if not 0.0 <= minimum_end_to_end_coverage <= 1.0:
        raise ValueError("minimum_end_to_end_coverage must be between zero and one")

    manifest = _load_manifest(Path(manifest_path))
    development = normalise_scores(
        pd.read_csv(development_scores_path, keep_default_na=False),
        name="development",
    )
    test = normalise_scores(
        pd.read_csv(test_scores_path, keep_default_na=False),
        name="test",
    )

    development_framework_qids = _validate_membership(
        manifest=manifest,
        scores=development,
        split="development",
    )
    test_framework_qids = _validate_membership(
        manifest=manifest,
        scores=test,
        split="test",
    )

    curve: pd.DataFrame | None = None
    precision_constraint_met: bool | None = None
    selected_tau: float
    selection_mode: str

    if tau is None:
        taus = np.round(
            np.arange(tau_min, tau_max + tau_step / 2.0, tau_step),
            10,
        )
        curve = tau_curve(
            development,
            framework_queries=len(development_framework_qids),
            taus=taus,
        )
        selected_tau, precision_constraint_met = select_tau(
            curve,
            target_precision=target_precision,
            minimum_end_to_end_coverage=minimum_end_to_end_coverage,
        )
        selection_mode = "development_oof_auto"
    else:
        selected_tau = float(tau)
        selection_mode = "manual_tau"

    development_result, development_decisions = evaluate_tau(
        development,
        framework_queries=len(development_framework_qids),
        tau=selected_tau,
        name="Development four-fold OOF threshold performance",
    )
    test_result, test_decisions = evaluate_tau(
        test,
        framework_queries=len(test_framework_qids),
        tau=selected_tau,
        name="Held-out test threshold performance",
    )

    summary = pd.DataFrame([development_result, test_result])
    decisions = pd.concat(
        [
            development_decisions.assign(split="development"),
            test_decisions.assign(split="test"),
        ],
        ignore_index=True,
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / "tau_margin_summary.csv", index=False)
    decisions.to_csv(output_dir / "tau_margin_query_decisions.csv", index=False)
    if curve is not None:
        curve.to_csv(output_dir / "tau_margin_development_oof_curve.csv", index=False)

    metadata = {
        "selection_mode": selection_mode,
        "selected_tau_margin": selected_tau,
        "target_precision": target_precision if tau is None else None,
        "minimum_end_to_end_coverage": (
            minimum_end_to_end_coverage if tau is None else None
        ),
        "precision_constraint_met": precision_constraint_met,
        "manifest": str(Path(manifest_path)),
        "development_scores": str(Path(development_scores_path)),
        "test_scores": str(Path(test_scores_path)),
    }
    (output_dir / "calibration_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    if base_config_path is not None or config_output_path is not None:
        if base_config_path is None or config_output_path is None:
            raise ValueError(
                "base_config_path and config_output_path must be supplied together"
            )
        _write_runtime_config(
            base_config_path=Path(base_config_path),
            output_path=Path(config_output_path),
            tau=selected_tau,
            target_precision=target_precision if tau is None else None,
            minimum_end_to_end_coverage=(
                minimum_end_to_end_coverage if tau is None else None
            ),
            precision_constraint_met=precision_constraint_met,
            development_result=development_result,
            test_result=test_result,
        )

    return summary, curve, decisions
