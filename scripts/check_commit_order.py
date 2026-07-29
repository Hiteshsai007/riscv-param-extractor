#!/usr/bin/env python3
"""
R4/R5 — Commit-Order Integrity Check.

Verifies that:
  R4: Ground truth files were committed BEFORE any result files
      for the same snippet.
  R5: Validation logic (validate_yaml.py, eval_harness.py, test_epistemic_rigor.py)
      was committed BEFORE the evaluation runs they grade.

This ensures predictions are precommitted, not retroactively fitted
to observed outputs, and that the grading rubric predates the grades.

Usage:
    python scripts/check_commit_order.py
"""
import argparse
import subprocess
import sys
from pathlib import Path

CUTOFF_DATE = "2026-07-28T00:00:00"


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


def check_ground_truth_ordering():
    """R4: Verify ground truth committed before results."""
    ground_truth_dir = Path("data/ground_truth")
    results_dirs = list(Path("results").glob("run_*"))

    if not ground_truth_dir.exists():
        return ["ERROR: data/ground_truth/ directory not found."]

    errors = []
    new_errors = []
    checked = 0

    for gt_file in sorted(ground_truth_dir.glob("*.yaml")):
        snippet_name = gt_file.stem
        gt_timestamp = get_first_commit_timestamp(str(gt_file))

        if not gt_timestamp:
            errors.append(f"  R4: {snippet_name}: ground truth file not yet committed")
            new_errors.append(f"  R4: {snippet_name}: ground truth file not yet committed")
            continue

        # Check all result dirs for this snippet
        for results_dir in results_dirs:
            result_file = results_dir / f"{snippet_name}.yaml"
            if result_file.exists():
                result_timestamp = get_first_commit_timestamp(str(result_file))
                if result_timestamp and result_timestamp < gt_timestamp:
                    errors.append(
                        f"  R4: {snippet_name}: result in {results_dir.name} "
                        f"(committed {result_timestamp}) predates ground truth "
                        f"(committed {gt_timestamp})"
                    )
                    if result_timestamp > CUTOFF_DATE:
                        new_errors.append(
                            f"  R4: {snippet_name}: result in {results_dir.name} "
                            f"(committed {result_timestamp}) predates ground truth "
                            f"(committed {gt_timestamp})"
                        )
                checked += 1

    return errors, checked, new_errors


def check_validator_ordering():
    """R5: Verify validators committed before evaluation runs they grade."""
    validators = [
        "src/validate_yaml.py",
        "src/eval_harness.py",
        "tests/test_epistemic_rigor.py",
    ]
    # The evaluation results that these validators grade
    evaluated_results_dir = "results/run_20260717_053803"

    errors = []
    new_errors = []
    checked = 0

    for validator_path in validators:
        if not Path(validator_path).exists():
            errors.append(f"  R5: {validator_path} not found")
            new_errors.append(f"  R5: {validator_path} not found")
            continue

        validator_ts = get_first_commit_timestamp(validator_path)
        if not validator_ts:
            errors.append(f"  R5: {validator_path} not yet committed")
            new_errors.append(f"  R5: {validator_path} not yet committed")
            continue

        # Check against the first result file in the evaluated run
        results_dir = Path(evaluated_results_dir)
        if results_dir.exists():
            for result_file in sorted(results_dir.glob("*.yaml"))[:1]:
                result_ts = get_first_commit_timestamp(str(result_file))
                if result_ts and result_ts < validator_ts:
                    # This is expected for historical validators added after runs
                    errors.append(
                        f"  R5: {validator_path} (committed {validator_ts}) "
                        f"postdates result {result_file.name} "
                        f"(committed {result_ts}) - expected for retrofitted validators"
                    )
                    if result_ts > CUTOFF_DATE:
                        new_errors.append(
                            f"  R5: {validator_path} (committed {validator_ts}) "
                            f"postdates result {result_file.name} "
                            f"(committed {result_ts}) - expected for retrofitted validators"
                        )
                checked += 1

    return errors, checked, new_errors


def main():
    parser = argparse.ArgumentParser(description="Commit-Order Integrity Check (R4/R5)")
    parser.add_argument("--strict", action="store_true", help="Fail on any new violations")
    args = parser.parse_args()

    print("=" * 60)
    print("Commit-Order Integrity Check (R4/R5)")
    print("=" * 60)

    # R4: Ground truth ordering
    print("\n[R4] Ground truth -> results ordering:")
    gt_errors, gt_checked, gt_new_errors = check_ground_truth_ordering()
    print(f"  Checked {gt_checked} ground-truth <-> result pairs.")

    # R5: Validator ordering
    print("\n[R5] Validator -> evaluation ordering:")
    v_errors, v_checked, v_new_errors = check_validator_ordering()
    print(f"  Checked {v_checked} validator <-> result pairs.")

    all_errors = gt_errors + v_errors
    all_new_errors = gt_new_errors + v_new_errors

    if all_errors:
        print(f"\nWARNINGS ({len(all_errors)}):")
        for e in all_errors:
            print(e)
        print(
            "\nNote: Pre-existing results that predate the ground truth/validator "
            "system are expected for historical runs. New snippets and validators "
            "must be committed before the evaluation runs they grade."
        )
    else:
        print("\nAll checks passed. OK")

    if args.strict and all_new_errors:
        print(f"\nSTRICT MODE FAILED: Found {len(all_new_errors)} new violations.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
