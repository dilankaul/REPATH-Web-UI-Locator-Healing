"""Load the benchmark development and held-out test site groups."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SiteSplit:
    development_sites: tuple[str, ...]
    test_sites: tuple[str, ...]
    default_group: str = "test"
    expected_queries: dict[str, int] | None = None

    @property
    def sites(self) -> tuple[str, ...]:
        """Backward-compatible access to the configured default group."""
        return self.group(self.default_group)

    def group(self, name: str) -> tuple[str, ...]:
        normalized = name.casefold()
        if normalized == "development":
            return self.development_sites
        if normalized == "test":
            return self.test_sites
        if normalized == "all":
            return tuple(dict.fromkeys(self.development_sites + self.test_sites))
        raise KeyError(f"Unknown site group: {name}")

    def expected_for(self, name: str) -> int | None:
        if self.expected_queries is None:
            return None
        return self.expected_queries.get(name.casefold())


# Retained for imports used by earlier releases.
TestSplit = SiteSplit


def _site_list(payload: dict[str, Any], key: str, path: Path) -> tuple[str, ...]:
    values = payload.get(key, [])
    if not isinstance(values, list) or not all(isinstance(site, str) for site in values):
        raise ValueError(f"Expected a list of site names for '{key}' in {path}")
    return tuple(values)


def load_site_split(path: Path) -> SiteSplit:
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        payload: Any = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected a mapping in split config: {path}")

    # Accept the old single-test-list format as well as the new grouped format.
    development_sites = _site_list(payload, "development_sites", path)
    if "test_sites" in payload:
        test_sites = _site_list(payload, "test_sites", path)
    else:
        test_sites = _site_list(payload, "sites", path)

    default_group = str(payload.get("default_group", "test")).casefold()
    if default_group not in {"development", "test", "all"}:
        raise ValueError(f"Invalid default_group '{default_group}' in {path}")

    expected_payload = payload.get("expected_queries")
    expected: dict[str, int] | None
    if expected_payload is None:
        expected = None
    elif isinstance(expected_payload, dict):
        expected = {
            str(group).casefold(): int(value)
            for group, value in expected_payload.items()
        }
    elif isinstance(expected_payload, int):
        expected = {default_group: int(expected_payload)}
    else:
        raise ValueError(f"Invalid expected_queries in {path}")

    return SiteSplit(
        development_sites=development_sites,
        test_sites=test_sites,
        default_group=default_group,
        expected_queries=expected,
    )


def load_test_split(path: Path) -> SiteSplit:
    """Backward-compatible alias for :func:`load_site_split`."""
    return load_site_split(path)
