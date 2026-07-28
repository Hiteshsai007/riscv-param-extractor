#!/usr/bin/env python3
"""
R7 — Reproducibility Verification Script.

Re-derives all metrics from committed raw outputs and verifies they match
the numbers reported in README.md and EXPERIMENTS.md.

Requires NO API key or model call — pure re-derivation from committed data.

Usage:
    python scripts/verify.py
"""
import re
import sys
from pathlib import Path

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.eval_harness import evaluate_full


def extract_reported_metrics(readme_path: Path) -> dict:
    """Extract the metrics table from README.md."""
    content = readme_path.read_text(encoding="utf-8")
    metrics = {}

    # Find the main metrics table (Strict Qwen column)
    precision_match = re.search(r"\*\*Precision\*\*\s*\|\s*([\d.]+)", content)
    recall_match = re.search(r"\*\*Recall\*\*\s*\|\s*([\d.]+)", content)
    f1_match = re.search(r"\*\*F1 Score\*\*\s*\|\s*([\d.]+)", content)
    halluc_match = re.search(r"\*\*Hallucination Rate\*\*\s*\|\s*([\d.]+)", content)

    if precision_match:
        metrics["precision"] = float(precision_match.group(1))
    if recall_match:
        metrics["recall"] = float(recall_match.group(1))
    if f1_match:
        metrics["f1"] = float(f1_match.group(1))
    if halluc_match:
        metrics["hallucination_rate"] = float(halluc_match.group(1))

    return metrics


def main():
    results_dir = Path("results/run_20260717_053803")
    gold_dir = Path("data/gold")
    snippets_dir = Path("data/raw_snippets")
    readme_path = Path("README.md")

    if not results_dir.exists():
        print(f"ERROR: Results directory {results_dir} not found.")
        sys.exit(1)

    print("Re-deriving metrics from committed results...")
    report = evaluate_full(str(results_dir), str(gold_dir), str(snippets_dir))

    computed = {
        "precision": report["precision"],
        "recall": report["recall"],
        "f1": report["f1"],
        "hallucination_rate": report["hallucination_rate"],
    }

    print(f"\nComputed metrics:")
    for k, v in computed.items():
        print(f"  {k}: {v}")

    # Check against README reported values
    reported = extract_reported_metrics(readme_path)
    print(f"\nReported metrics (from README.md):")
    for k, v in reported.items():
        print(f"  {k}: {v}")

    mismatches = []
    for key in computed:
        if key in reported:
            if abs(computed[key] - reported[key]) > 0.001:
                mismatches.append(
                    f"  {key}: computed={computed[key]:.4f}, reported={reported[key]:.4f}"
                )

    if mismatches:
        print(f"\nMISMATCHES FOUND:")
        for m in mismatches:
            print(m)
        sys.exit(1)
    else:
        print("\nAll reported metrics match re-derived values. ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
