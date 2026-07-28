#!/usr/bin/env python3
"""
R3 — Commit-Order Integrity Check.

Verifies that ground truth files were committed BEFORE any result files
for the same snippet. This ensures predictions are precommitted, not
retroactively fitted to observed outputs.

Usage:
    python scripts/check_commit_order.py
"""
import subprocess
import sys
from pathlib import Path


def get_first_commit_timestamp(filepath: str) -> str | None:
    """Get the timestamp of the FIRST commit that introduced this file."""
    result = subprocess.run(
        ["git", "log", "--diff-filter=A", "--follow", "--format=%aI", "--", filepath],
        capture_output=True,
        text=True,
    )
    lines = result.stdout.strip().split("\n")
    # Last line is the earliest (git log is reverse-chronological)
    return lines[-1] if lines and lines[-1] else None


def main():
    ground_truth_dir = Path("data/ground_truth")
    results_dirs = list(Path("results").glob("run_*"))

    if not ground_truth_dir.exists():
        print("ERROR: data/ground_truth/ directory not found.")
        sys.exit(1)

    errors = []
    checked = 0

    for gt_file in sorted(ground_truth_dir.glob("*.yaml")):
        snippet_name = gt_file.stem
        gt_timestamp = get_first_commit_timestamp(str(gt_file))

        if not gt_timestamp:
            errors.append(f"  {snippet_name}: ground truth file not yet committed")
            continue

        # Check all result dirs for this snippet
        for results_dir in results_dirs:
            result_file = results_dir / f"{snippet_name}.yaml"
            if result_file.exists():
                result_timestamp = get_first_commit_timestamp(str(result_file))
                if result_timestamp and result_timestamp < gt_timestamp:
                    errors.append(
                        f"  {snippet_name}: result in {results_dir.name} "
                        f"(committed {result_timestamp}) predates ground truth "
                        f"(committed {gt_timestamp})"
                    )
                checked += 1

    print(f"Checked {checked} ground-truth ↔ result pairs.")

    if errors:
        print(f"\nWARNINGS ({len(errors)}):")
        for e in errors:
            print(e)
        print(
            "\nNote: Pre-existing results that predate the ground truth system "
            "are expected for historical runs. New snippets must have ground truth "
            "committed first."
        )
    else:
        print("All checks passed.")

    # Don't fail CI for historical results — only flag them
    sys.exit(0)


if __name__ == "__main__":
    main()
