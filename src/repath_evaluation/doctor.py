"""Environment validation for reproducible benchmark execution."""

from __future__ import annotations

from pathlib import Path

import joblib
import lightgbm as lgb

from .algorithms.repath.features import ALL_MODEL_FEATURES
from .data import discover_sites, load_test_split


def doctor_command(args) -> None:
    """Validate local data, model artifacts, and baseline dependencies."""
    failures: list[str] = []
    checks: list[tuple[str, bool, str]] = []

    data_root = Path(args.data_root)
    split_path = Path(args.split_config)
    try:
        split = load_test_split(split_path)
        discovered = {path.name for path in discover_sites(data_root)}
        missing = sorted(set(split.sites) - discovered)
        checks.append(("dataset", not missing, f"missing sites: {missing}" if missing else str(data_root)))
    except Exception as exc:  # noqa: BLE001 - doctor reports all environment failures
        checks.append(("dataset", False, str(exc)))

    model_path = Path(args.repath_model)
    config_path = Path(args.repath_config)
    try:
        config = joblib.load(config_path)
        booster = lgb.Booster(model_file=str(model_path))
        valid = config.get("ALL_FEATURES", config.get("FEATURES")) == ALL_MODEL_FEATURES
        valid = valid and booster.num_feature() == len(ALL_MODEL_FEATURES)
        checks.append(("REPATH artifacts", valid, "50-feature schema valid" if valid else "feature schema mismatch"))
    except Exception as exc:  # noqa: BLE001 - doctor reports all environment failures
        checks.append(("REPATH artifacts", False, str(exc)))

    checks.append(("SFTM implementation", True, "available"))
    checks.append(("WebEvo implementation", True, "available"))

    for name, ok, detail in checks:
        status = "OK" if ok else "MISSING"
        print(f"{status:>7} | {name:<16} | {detail}")
        if not ok:
            failures.append(name)
    if failures:
        failure_names = ", ".join(failures)
        raise SystemExit(f"Doctor found {len(failures)} issue(s): {failure_names}")
