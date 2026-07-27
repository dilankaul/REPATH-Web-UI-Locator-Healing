"""Shared timing statistics."""

import numpy as np


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(values, q)) if values else 0.0
