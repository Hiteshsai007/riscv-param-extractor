#!/usr/bin/env python3
"""
R6 — Zero-Call Reproducibility Verification Script.

Re-derives all published metrics from committed raw outputs and verifies
they match the numbers reported in README.md.

Requires NO API key, no model call, no network — pure re-derivation from
committed data. Runs in seconds. Exits non-zero on any mismatch.

Usage:
    python scripts/verify.py           # Verify all claims
    python scripts/verify.py --list    # Show which claims are checkable
"""
import argparse
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.eval_harness import evaluate_full


CHECKABLE_CLAIMS = {
    "precision_strict": {
        "description": "Strict precision (Qwen, Run 5, v6_decision_framework)",
        "readme_pattern": r"\*\*Precision\*\*\s*\|\s*([\d.]+)\s*\|",
        "report_path": ("aggregate", "precision"),
        "source": "Evaluation Metrics table, 'Exact Match' column",
    },
    "recall_strict": {
        "description": "Strict recall (Qwen, Run 5, v6_decision_framework)",
        "readme_pattern": r"\*\*Recall\*\*\s*\|\s*([\d.]+)\s*\|",
        "report_path": ("aggregate", "recall"),
        "source": "Evaluation Metrics table, 'Exact Match' column",
    },
    "f1_strict": {
        "description": "Strict F1 (Qwen, Run 5, v6_decision_framework)",
        "readme_pattern": r"\*\*F1 Score\*\*\s*\|\s*([\d.]+)\s*\|",
        "report_path": ("aggregate", "f1"),
        "source": "Evaluation Metrics table, 'Exact Match' column",
    },
    "hallucination_rate": {
        "description": "Hallucination rate (Qwen, Run 5)",
        "readme_pattern": r"\*\*Hallucination Rate\*\*\s*\|\s*([\d.]+)%",
        "report_path": ("aggregate", "hallucination_rate"),
        "source": "Evaluation Metrics table",
        "transform": lambda x: x * 100,  # README reports as percentage
    },
}

NOT_CHECKABLE = [
    "Relaxed precision/recall/F1 — reported in README but requires re-running "
    "the relaxed matcher. This IS checkable via evaluate_full() but not yet "
    "wired into the verification table.",
    "Llama 3.1 8B metrics — all marked N/A (Failed) because the run never completed.",
    "Grounding vs discovery recall split — labeled 'N/A (not separately computed)' "
    "in README. Would require per-snippet recall decomposition.",
    "Run-to-run variance — requires re-running the pipeline with identical config. "
    "Not checkable offline.",
]


def extract_reported_metrics(readme_path: Path) -> dict:
    """Extract the metrics table from README.md."""
    content = readme_path.read_text(encoding="utf-8")
    metrics = {}

    for claim_id, claim in CHECKABLE_CLAIMS.items():
        match = re.search(claim["readme_pattern"], content)
        if match:
            metrics[claim_id] = float(match.group(1))
        else:
            metrics[claim_id] = None

    return metrics


def resolve_report_value(report: dict, path: tuple) -> float:
    """Navigate nested dict by path tuple."""
    current = report
    for key in path:
        current = current[key]
    return current


def do_verify():
    """Main verification logic."""
    results_dir = Path("results/run_20260717_053803")
    gold_dir = Path("data/gold")
    snippets_dir = Path("data/raw_snippets")
    readme_path = Path("README.md")

    if not results_dir.exists():
        print(f"ERROR: Results directory {results_dir} not found.")
        sys.exit(1)

    if not readme_path.exists():
        print(f"ERROR: README.md not found.")
        sys.exit(1)

    print("Re-deriving metrics from committed results (zero API calls)...")
    report = evaluate_full(str(results_dir), str(gold_dir), str(snippets_dir))

    # Extract README-reported values
    reported = extract_reported_metrics(readme_path)

    print(f"\n{'Claim':<25} {'Computed':>10} {'Reported':>10} {'Status':>8}")
    print("-" * 60)

    mismatches = []

    for claim_id, claim in CHECKABLE_CLAIMS.items():
        computed_raw = resolve_report_value(report, claim["report_path"])
        transform = claim.get("transform")
        computed = transform(computed_raw) if transform else computed_raw

        reported_val = reported.get(claim_id)

        if reported_val is None:
            status = "MISSING"
            print(f"{claim_id:<25} {computed:>10.4f} {'???':>10} {status:>8}")
            mismatches.append(f"  {claim_id}: not found in README.md")
        elif abs(computed - reported_val) > 0.01:
            status = "FAIL"
            print(f"{claim_id:<25} {computed:>10.4f} {reported_val:>10.4f} {status:>8}")
            mismatches.append(
                f"  {claim_id}: computed={computed:.4f}, reported={reported_val:.4f}"
            )
        else:
            status = "OK"
            print(f"{claim_id:<25} {computed:>10.4f} {reported_val:>10.4f} {status:>8}")

    if mismatches:
        print(f"\nMISMATCHES FOUND ({len(mismatches)}):")
        for m in mismatches:
            print(m)
        sys.exit(1)
    else:
        print("\nAll checkable claims match re-derived values. OK")
        sys.exit(0)


def do_list():
    """Show which claims are checkable and which are not."""
    print("=== CHECKABLE CLAIMS ===")
    print("These are verified by re-deriving from committed artifacts:\n")
    for claim_id, claim in CHECKABLE_CLAIMS.items():
        print(f"  [{claim_id}] {claim['description']}")
        print(f"    Source: {claim['source']}")
        print()

    print("=== NOT CHECKABLE (honestly labeled) ===")
    print("These claims are NOT verified by this script:\n")
    for note in NOT_CHECKABLE:
        print(f"  • {note}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Verify all published metrics match committed artifacts (R6)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Show which claims are checkable and which are not",
    )
    args = parser.parse_args()

    if args.list:
        do_list()
    else:
        do_verify()


if __name__ == "__main__":
    main()
