from __future__ import annotations

import argparse
from pathlib import Path

from repath_evaluation.data import discover_sites, load_page_pair, load_site_split
from repath_evaluation.evaluation import build_queries


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a configured REPATH evaluation site group")
    parser.add_argument(
        "data_root",
        nargs="?",
        default="data",
        help="Dataset directory containing the UITestFix site folders (default: data)",
    )
    parser.add_argument("--split-config", default="configs/site_split.yaml")
    parser.add_argument(
        "--sites",
        choices=["test", "development", "all"],
        default="test",
        help="Configured site group to validate (default: test)",
    )
    args = parser.parse_args()

    split = load_site_split(Path(args.split_config))
    selected_sites = split.group(args.sites)
    paths = {path.name: path for path in discover_sites(Path(args.data_root))}
    missing = set(selected_sites) - paths.keys()
    if missing:
        raise SystemExit(f"Missing sites: {sorted(missing)}")

    total = 0
    for site in selected_sites:
        pair = load_page_pair(paths[site])
        count = sum(query.eligible for query in build_queries(pair))
        total += count
        print(f"{site}: {count}")
    print(f"Total: {total}")

    expected = split.expected_for(args.sites)
    if expected is not None and total != expected:
        raise SystemExit(f"Expected {expected} eligible queries")


if __name__ == "__main__":
    main()
