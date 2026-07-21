"""
Evaluation Harness — Precision/Recall/Hallucination/Validity scoring.

Computes all metrics defined in the PRD:
1. Precision: extracted ∩ gold / extracted (strict and relaxed modes)
2. Recall: extracted ∩ gold / gold (strict and relaxed modes)
3. Hallucination rate: % evidence fields failing exact substring match
4. YAML validity rate: % outputs passing schema validation on first attempt
5. Consistency: field-level diff across repeated runs (same seed/temp)
6. Cross-model agreement: Jaccard overlap between two models' parameter sets

Usage:
    python -m src.eval_harness --results results/run_X.yaml --gold data/gold/
    python -m src.eval_harness --compare results/model_a/ results/model_b/
"""

import argparse
import difflib
import json
import logging
import re
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


def _normalize_name(name: str) -> str:
    """
    Normalize a parameter name for relaxed comparison.

    Lowercases, strips whitespace, replaces hyphens/spaces with underscores,
    and collapses multiple underscores.
    """
    name = name.strip().lower()
    name = re.sub(r'[\s\-]+', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


def _name_similarity(name_a: str, name_b: str) -> float:
    """
    Compute normalized string similarity between two parameter names.

    Uses difflib.SequenceMatcher on normalized names. Returns a float
    in [0.0, 1.0] where 1.0 is an exact match.
    """
    norm_a = _normalize_name(name_a)
    norm_b = _normalize_name(name_b)
    return difflib.SequenceMatcher(None, norm_a, norm_b).ratio()


DEFAULT_RELAXED_THRESHOLD = 0.75


def compute_precision_recall_relaxed(
    extracted: list[dict[str, Any]],
    gold: list[dict[str, Any]],
    name_similarity_threshold: float = DEFAULT_RELAXED_THRESHOLD,
) -> dict[str, Any]:
    """
    Compute precision and recall using relaxed name matching.

    Matching uses normalized string similarity on `name` (threshold >= 0.8)
    combined with exact `type` match. This addresses the evaluation brittleness
    documented in EXPERIMENTS.md where semantically equivalent parameter names
    (e.g., `cache_block_operation_mechanism` vs `non_coherent_agent_cbo_mechanism`)
    are counted as mismatches under strict matching.

    The strict metric is NOT replaced — this is purely additive.

    Returns:
        Dict with precision, recall, f1, and match details.
    """
    # Build lists of (name, type) for matching
    extracted_items = [
        {
            "name": p.get("name", "").strip().lower(),
            "type": p.get("type", "").strip().lower(),
            "key": _parameter_key(p),
        }
        for p in extracted
    ]
    gold_items = [
        {
            "name": p.get("name", "").strip().lower(),
            "type": p.get("type", "").strip().lower(),
            "key": _parameter_key(p),
        }
        for p in gold
    ]

    # Greedy matching: for each extracted param, find best gold match
    matched_gold_indices: set[int] = set()
    tp_matches: list[dict[str, Any]] = []
    fp_keys: list[str] = []

    for ext in extracted_items:
        best_match_idx = -1
        best_similarity = 0.0

        for g_idx, gold_item in enumerate(gold_items):
            if g_idx in matched_gold_indices:
                continue
            # Exact type match required
            if ext["type"] != gold_item["type"]:
                continue
            sim = _name_similarity(ext["name"], gold_item["name"])
            if sim >= name_similarity_threshold and sim > best_similarity:
                best_similarity = sim
                best_match_idx = g_idx

        if best_match_idx >= 0:
            matched_gold_indices.add(best_match_idx)
            tp_matches.append({
                "extracted": ext["key"],
                "gold": gold_items[best_match_idx]["key"],
                "name_similarity": round(best_similarity, 4),
            })
        else:
            fp_keys.append(ext["key"])

    fn_keys = [
        gold_items[i]["key"]
        for i in range(len(gold_items))
        if i not in matched_gold_indices
    ]

    tp = len(tp_matches)
    fp = len(fp_keys)
    fn = len(fn_keys)

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
        "name_similarity_threshold": name_similarity_threshold,
        "matches": tp_matches,
        "false_positive_keys": sorted(fp_keys),
        "false_negative_keys": sorted(fn_keys),
    }


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


def compute_cross_model_agreement(
    extracted_a: list[dict[str, Any]],
    extracted_b: list[dict[str, Any]],
    model_a_name: str = "model_a",
    model_b_name: str = "model_b",
) -> dict[str, Any]:
    """
    Compute Jaccard similarity and agreement metrics between two models.
    """
    keys_a = {_parameter_key(p) for p in extracted_a}
    keys_b = {_parameter_key(p) for p in extracted_b}

    intersection = keys_a & keys_b
    union = keys_a | keys_b
    
    jaccard = len(intersection) / len(union) if union else 1.0

    return {
        "jaccard_similarity": round(jaccard, 4),
        "total_agreed": len(intersection),
        f"{model_a_name}_total": len(keys_a),
        f"{model_b_name}_total": len(keys_b),
        "agreed_keys": sorted(intersection),
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
    aggregate_pr_strict = compute_precision_recall(all_extracted, all_gold)
    aggregate_pr_relaxed = compute_precision_recall_relaxed(all_extracted, all_gold)
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
            "precision": aggregate_pr_strict["precision"],
            "recall": aggregate_pr_strict["recall"],
            "f1": aggregate_pr_strict["f1"],
            "hallucination_rate": round(aggregate_hallucination["rate"], 4),
            "yaml_validity_rate": round(aggregate_validity["rate"], 4),
            "total_extracted": len(all_extracted),
            "total_gold": len(all_gold),
        },
        "aggregate_relaxed": {
            "precision": aggregate_pr_relaxed["precision"],
            "recall": aggregate_pr_relaxed["recall"],
            "f1": aggregate_pr_relaxed["f1"],
            "name_similarity_threshold": aggregate_pr_relaxed["name_similarity_threshold"],
            "matches": aggregate_pr_relaxed["matches"],
        },
        "per_snippet": per_snippet_results,
        "hallucination_details": all_hallucination_details,
        "validity_errors": all_validity_details,
        "precision_recall_detail": aggregate_pr_strict,
    }


def generate_disagreement_report(
    results_dir_a: str | Path,
    results_dir_b: str | Path,
    gold_dir: str | Path,
    snippets_dir: str | Path,
    model_a_name: str = "model_a",
    model_b_name: str = "model_b",
) -> dict[str, Any]:
    """
    Generate a detailed disagreement report between two models' extraction results.

    Identifies:
    - Parameters found by model A but not B (and vice versa)
    - Parameters found by both but with different `type`
    - Parameters found by both but with different `confidence`
    - Per-model metrics against gold labels

    Returns:
        Structured report suitable for embedding in EXPERIMENTS.md.
    """
    results_dir_a = Path(results_dir_a)
    results_dir_b = Path(results_dir_b)
    snippets_dir = Path(snippets_dir)

    # Evaluate each model
    report_a = evaluate_full(results_dir_a, gold_dir, snippets_dir)
    report_b = evaluate_full(results_dir_b, gold_dir, snippets_dir)

    # Collect all parameters per model across all snippets
    all_params_a: dict[str, list[dict[str, Any]]] = {}  # snippet -> params
    all_params_b: dict[str, list[dict[str, Any]]] = {}

    # Get all snippet names from both result dirs
    snippet_names = set()
    for f in results_dir_a.glob("*.yaml"):
        if f.stem not in ("manifest", "summary"):
            snippet_names.add(f.stem)
    for f in results_dir_b.glob("*.yaml"):
        if f.stem not in ("manifest", "summary"):
            snippet_names.add(f.stem)

    disagreements = []

    for snippet_name in sorted(snippet_names):
        # Load results from both models
        file_a = results_dir_a / f"{snippet_name}.yaml"
        file_b = results_dir_b / f"{snippet_name}.yaml"

        params_a = []
        params_b = []

        if file_a.exists():
            with open(file_a, "r", encoding="utf-8") as f:
                data_a = yaml.safe_load(f) or {}
            params_a = data_a.get("parameters", [])

        if file_b.exists():
            with open(file_b, "r", encoding="utf-8") as f:
                data_b = yaml.safe_load(f) or {}
            params_b = data_b.get("parameters", [])

        all_params_a[snippet_name] = params_a
        all_params_b[snippet_name] = params_b

        # Find disagreements
        keys_a = {_parameter_key(p): p for p in params_a}
        keys_b = {_parameter_key(p): p for p in params_b}

        # Parameters found by A only
        for key in sorted(set(keys_a) - set(keys_b)):
            disagreements.append({
                "snippet": snippet_name,
                "type": "found_by_a_only",
                "parameter_key": key,
                f"{model_a_name}_value": {
                    "name": keys_a[key].get("name"),
                    "type": keys_a[key].get("type"),
                    "confidence": keys_a[key].get("confidence"),
                },
            })

        # Parameters found by B only
        for key in sorted(set(keys_b) - set(keys_a)):
            disagreements.append({
                "snippet": snippet_name,
                "type": "found_by_b_only",
                "parameter_key": key,
                f"{model_b_name}_value": {
                    "name": keys_b[key].get("name"),
                    "type": keys_b[key].get("type"),
                    "confidence": keys_b[key].get("confidence"),
                },
            })

        # Check for same-name-different-type or different-confidence
        # Use relaxed name matching to find corresponding params
        for p_a in params_a:
            name_a = p_a.get("name", "").strip().lower()
            for p_b in params_b:
                name_b = p_b.get("name", "").strip().lower()
                sim = _name_similarity(name_a, name_b)
                if sim >= DEFAULT_RELAXED_THRESHOLD:
                    type_a = p_a.get("type", "").strip().lower()
                    type_b = p_b.get("type", "").strip().lower()
                    conf_a = p_a.get("confidence", "").strip().lower()
                    conf_b = p_b.get("confidence", "").strip().lower()

                    if type_a != type_b:
                        disagreements.append({
                            "snippet": snippet_name,
                            "type": "type_disagreement",
                            f"{model_a_name}_name": name_a,
                            f"{model_b_name}_name": name_b,
                            "name_similarity": round(sim, 4),
                            f"{model_a_name}_type": type_a,
                            f"{model_b_name}_type": type_b,
                        })
                    elif conf_a != conf_b:
                        disagreements.append({
                            "snippet": snippet_name,
                            "type": "confidence_disagreement",
                            "parameter_name": name_a,
                            f"{model_a_name}_confidence": conf_a,
                            f"{model_b_name}_confidence": conf_b,
                        })

    # Cross-model agreement (Jaccard)
    flat_a = [p for params in all_params_a.values() for p in params]
    flat_b = [p for params in all_params_b.values() for p in params]
    agreement = compute_cross_model_agreement(
        flat_a, flat_b, model_a_name, model_b_name
    )

    return {
        "model_a": {
            "name": model_a_name,
            "metrics": report_a["aggregate"],
            "metrics_relaxed": report_a.get("aggregate_relaxed", {}),
        },
        "model_b": {
            "name": model_b_name,
            "metrics": report_b["aggregate"],
            "metrics_relaxed": report_b.get("aggregate_relaxed", {}),
        },
        "cross_model_agreement": agreement,
        "disagreements": disagreements,
        "total_disagreements": len(disagreements),
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
