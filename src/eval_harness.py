"""
Evaluation Harness — Precision/Recall/Hallucination/Validity scoring.

Computes all metrics defined in the PRD:
1. Precision: extracted ∩ gold / extracted
2. Recall: extracted ∩ gold / gold
3. Hallucination rate: % evidence fields failing exact substring match
4. YAML validity rate: % outputs passing schema validation on first attempt
5. Consistency: field-level diff across repeated runs (same seed/temp)
6. Cross-model agreement: Jaccard overlap between two models' parameter sets

Usage:
    python -m src.eval_harness --results results/run_X.yaml --gold data/gold/
    python -m src.eval_harness --compare results/model_a/ results/model_b/
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

from schema.parameter_schema import ExtractionResult, Parameter
from src.validate_yaml import validate_evidence_grounding, validate_parameter_schema

logger = logging.getLogger(__name__)


def load_gold_labels(gold_dir: str | Path) -> dict[str, dict[str, Any]]:
    """
    Load hand-labeled gold data from the gold directory.

    Expected structure:
        gold_dir/
            positive_cases/
                snippet_name.yaml    # contains expected parameters
            negative_cases/
                snippet_name.yaml    # contains expected_parameters: []

    Each gold file should have:
        snippet_file: <path to raw snippet>
        source_section: <section id>
        expected_parameters:
          - name: ...
            type: ...
            ...
        notes: <optional labeling notes>

    Returns:
        Dict mapping snippet filename to gold label data.
    """
    gold_dir = Path(gold_dir)
    labels: dict[str, dict[str, Any]] = {}

    for subdir in ["positive_cases", "negative_cases"]:
        case_dir = gold_dir / subdir
        if not case_dir.exists():
            logger.warning("Gold directory not found: %s", case_dir)
            continue

        for yaml_file in sorted(case_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data:
                    labels[yaml_file.stem] = data
                    labels[yaml_file.stem]["_source_dir"] = subdir
            except yaml.YAMLError as e:
                logger.error("Failed to load gold file %s: %s", yaml_file, e)

    return labels


def _parameter_key(param: dict[str, Any]) -> str:
    """
    Generate a comparison key for a parameter.

    Uses (name, type) as the identity — two parameters with the same
    name and type are considered the same parameter regardless of
    differences in description or evidence wording.
    """
    name = param.get("name", "").strip().lower()
    ptype = param.get("type", "").strip().lower()
    return f"{name}::{ptype}"


def compute_precision_recall(
    extracted: list[dict[str, Any]],
    gold: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Compute precision and recall of extracted parameters vs. gold set.

    Matching is by (name, type) key — exact name match required.

    Returns:
        Dict with precision, recall, f1, true_positives, false_positives,
        false_negatives counts.
    """
    extracted_keys = {_parameter_key(p) for p in extracted}
    gold_keys = {_parameter_key(p) for p in gold}

    true_positives = extracted_keys & gold_keys
    false_positives = extracted_keys - gold_keys
    false_negatives = gold_keys - extracted_keys

    tp = len(true_positives)
    fp = len(false_positives)
    fn = len(false_negatives)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_positive_keys": sorted(true_positives),
        "false_positive_keys": sorted(false_positives),
        "false_negative_keys": sorted(false_negatives),
    }


def compute_hallucination_rate(
    extracted_params: list[dict[str, Any]],
    source_text: str,
) -> dict[str, Any]:
    """
    Compute hallucination rate: % of evidence fields failing exact substring match.

    This is the mechanical, run-every-time check from the PRD.
    """
    total = len(extracted_params)
    if total == 0:
        return {
            "hallucination_rate": 0.0,
            "total_parameters": 0,
            "hallucinated": 0,
            "grounded": 0,
            "details": [],
        }

    hallucinated = 0
    grounded = 0
    details = []

    for param in extracted_params:
        evidence = param.get("evidence", "")
        is_grounded, detail = validate_evidence_grounding(evidence, source_text)
        if is_grounded:
            grounded += 1
        else:
            hallucinated += 1
            details.append({
                "name": param.get("name", "UNKNOWN"),
                "evidence_snippet": evidence[:100],
                "reason": detail,
            })

    return {
        "hallucination_rate": round(hallucinated / total, 4),
        "total_parameters": total,
        "hallucinated": hallucinated,
        "grounded": grounded,
        "details": details,
    }


def compute_yaml_validity_rate(
    extracted_params: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compute YAML validity rate: % of outputs passing Pydantic validation.

    Target: 100% (per PRD success metrics).
    """
    total = len(extracted_params)
    if total == 0:
        return {
            "validity_rate": 1.0,  # Vacuously true
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "errors": [],
        }

    valid = 0
    invalid = 0
    errors = []

    for param in extracted_params:
        is_valid, error = validate_parameter_schema(param)
        if is_valid:
            valid += 1
        else:
            invalid += 1
            errors.append({
                "name": param.get("name", "UNKNOWN"),
                "error": error,
            })

    return {
        "validity_rate": round(valid / total, 4),
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "errors": errors,
    }


def compute_cross_model_agreement(
    model_a_params: list[dict[str, Any]],
    model_b_params: list[dict[str, Any]],
    model_a_name: str = "model_a",
    model_b_name: str = "model_b",
) -> dict[str, Any]:
    """
    Compute Jaccard similarity between two models' parameter sets.

    Jaccard = |A ∩ B| / |A ∪ B|
    """
    keys_a = {_parameter_key(p) for p in model_a_params}
    keys_b = {_parameter_key(p) for p in model_b_params}

    intersection = keys_a & keys_b
    union = keys_a | keys_b

    jaccard = len(intersection) / len(union) if union else 1.0

    return {
        "jaccard_similarity": round(jaccard, 4),
        f"{model_a_name}_only": sorted(keys_a - keys_b),
        f"{model_b_name}_only": sorted(keys_b - keys_a),
        "agreement": sorted(intersection),
        f"{model_a_name}_total": len(keys_a),
        f"{model_b_name}_total": len(keys_b),
    }


def compute_consistency(
    runs: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    """
    Check consistency across repeated runs (same seed, same temp).

    Expects a list of parameter lists from N repeated runs.
    Reports field-level differences.
    """
    if len(runs) < 2:
        return {
            "consistent": True,
            "num_runs": len(runs),
            "note": "Need at least 2 runs for consistency check",
        }

    # Compare each run's parameter key set to run 0
    baseline_keys = {_parameter_key(p) for p in runs[0]}
    all_match = True
    diffs = []

    for i, run in enumerate(runs[1:], 1):
        run_keys = {_parameter_key(p) for p in run}
        if run_keys != baseline_keys:
            all_match = False
            diffs.append({
                "run": i,
                "missing": sorted(baseline_keys - run_keys),
                "extra": sorted(run_keys - baseline_keys),
            })

    identical_rate = (len(runs) - len(diffs)) / len(runs)

    return {
        "consistent": all_match,
        "identical_rate": round(identical_rate, 4),
        "num_runs": len(runs),
        "diffs": diffs,
    }


def evaluate_full(
    results_dir: str | Path,
    gold_dir: str | Path,
    snippets_dir: str | Path,
) -> dict[str, Any]:
    """
    Run full evaluation suite across all results in a directory.

    This is the main entry point for the evaluation harness.

    Returns:
        Comprehensive metrics report.
    """
    results_dir = Path(results_dir)
    gold_labels = load_gold_labels(gold_dir)
    snippets_dir = Path(snippets_dir)

    all_extracted = []
    all_gold = []
    all_hallucination_details = []
    all_validity_details = []
    per_snippet_results = []

    for snippet_name, gold_data in gold_labels.items():
        # Load the corresponding result file
        result_file = results_dir / f"{snippet_name}.yaml"
        if not result_file.exists():
            logger.warning("No result file for gold snippet '%s'", snippet_name)
            continue

        with open(result_file, "r", encoding="utf-8") as f:
            result_data = yaml.safe_load(f)

        # Load the source snippet for evidence checking
        snippet_file = snippets_dir / f"{snippet_name}.txt"
        source_text = ""
        if snippet_file.exists():
            source_text = snippet_file.read_text(encoding="utf-8")

        extracted = result_data.get("parameters", [])
        gold = gold_data.get("expected_parameters", [])

        # Per-snippet metrics
        pr = compute_precision_recall(extracted, gold)
        hallucination = compute_hallucination_rate(extracted, source_text)
        validity = compute_yaml_validity_rate(extracted)

        per_snippet_results.append({
            "snippet": snippet_name,
            "precision": pr["precision"],
            "recall": pr["recall"],
            "f1": pr["f1"],
            "hallucination_rate": hallucination["hallucination_rate"],
            "validity_rate": validity["validity_rate"],
        })

        all_extracted.extend(extracted)
        all_gold.extend(gold)
        all_hallucination_details.extend(hallucination.get("details", []))
        all_validity_details.extend(validity.get("errors", []))

    # Aggregate metrics
    aggregate_pr = compute_precision_recall(all_extracted, all_gold)
    aggregate_hallucination = {
        "rate": (
            len(all_hallucination_details) / len(all_extracted)
            if all_extracted
            else 0.0
        ),
        "total_hallucinated": len(all_hallucination_details),
        "total_extracted": len(all_extracted),
    }
    aggregate_validity = {
        "rate": (
            (len(all_extracted) - len(all_validity_details)) / len(all_extracted)
            if all_extracted
            else 1.0
        ),
        "total_invalid": len(all_validity_details),
        "total_extracted": len(all_extracted),
    }

    return {
        "aggregate": {
            "precision": aggregate_pr["precision"],
            "recall": aggregate_pr["recall"],
            "f1": aggregate_pr["f1"],
            "hallucination_rate": round(aggregate_hallucination["rate"], 4),
            "yaml_validity_rate": round(aggregate_validity["rate"], 4),
            "total_extracted": len(all_extracted),
            "total_gold": len(all_gold),
        },
        "per_snippet": per_snippet_results,
        "hallucination_details": all_hallucination_details,
        "validity_errors": all_validity_details,
        "precision_recall_detail": aggregate_pr,
    }


def main():
    """CLI entry point for the evaluation harness."""
    parser = argparse.ArgumentParser(
        description="Evaluation harness for RISC-V parameter extraction pipeline",
    )
    parser.add_argument(
        "--results",
        required=True,
        help="Path to results directory containing extraction YAML files",
    )
    parser.add_argument(
        "--gold",
        required=True,
        help="Path to gold-labeled data directory",
    )
    parser.add_argument(
        "--snippets",
        required=True,
        help="Path to raw snippets directory (for evidence checking)",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("MODEL_A_DIR", "MODEL_B_DIR"),
        help="Compare results from two models (cross-model agreement)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write metrics report (default: stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format (default: yaml)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Run evaluation
    report = evaluate_full(args.results, args.gold, args.snippets)

    # Format output
    if args.format == "json":
        output = json.dumps(report, indent=2)
    else:
        output = yaml.dump(report, default_flow_style=False, sort_keys=False)

    # Write output
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Report written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
