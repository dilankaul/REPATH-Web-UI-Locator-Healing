"""Reproducibility metadata for benchmark runs."""

import platform
import sys
from datetime import datetime, timezone

from ..algorithms.sftm import (
    UPSTREAM_COMMIT as SFTM_COMMIT,
    UPSTREAM_REPOSITORY as SFTM_REPOSITORY,
)
from ..algorithms.similo import (
    UPSTREAM_COMMIT as SIMILO_COMMIT,
    UPSTREAM_REPOSITORY as SIMILO_REPOSITORY,
)
from ..algorithms.vista import (
    UPSTREAM_COMMIT as VISTA_COMMIT,
    UPSTREAM_REPOSITORY as VISTA_REPOSITORY,
)
from ..algorithms.water import (
    UPSTREAM_COMMIT as WATER_COMMIT,
    UPSTREAM_REPOSITORY as WATER_REPOSITORY,
)
from ..algorithms.webevo import (
    UPSTREAM_COMMIT as WEBEVO_COMMIT,
    UPSTREAM_REPOSITORY as WEBEVO_REPOSITORY,
)


def metadata(arguments: dict) -> dict:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "arguments": arguments,
        "algorithm_sources": {
            "water": {
                "repository": WATER_REPOSITORY,
                "commit": WATER_COMMIT,
                "implementation": "python-port",
            },
            "vista": {
                "repository": VISTA_REPOSITORY,
                "commit": VISTA_COMMIT,
                "implementation": "python-port",
            },
            "similo": {
                "repository": SIMILO_REPOSITORY,
                "commit": SIMILO_COMMIT,
                "implementation": "python-port",
                "scope": "14-property manually weighted Similo locator",
            },
            "sftm": {
                "repository": SFTM_REPOSITORY,
                "commit": SFTM_COMMIT,
                "implementation": "python-port",
            },
            "webevo": {
                "repository": WEBEVO_REPOSITORY,
                "commit": WEBEVO_COMMIT,
                "implementation": "python-port",
                "scope": "semantics-based visual-search module",
            },
        },
    }
