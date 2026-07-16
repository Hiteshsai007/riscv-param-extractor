"""
YAML Validation Module — Schema + evidence-grounding checks.

Provides standalone validation functions that can be used by:
1. The extraction pipeline (inline validation)
2. The evaluation harness (validating stored results)
3. Unit tests

Separating validation from extraction allows re-validation of
stored results without re-running the LLM.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from schema.parameter_schema import ExtractionResult, Parameter

logger = logging.getLogger(__name__)


def validate_parameter_schema(param_dict: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate a single parameter dict against the Pydantic schema.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    try:
        Parameter(**param_dict)
        return True, ""
    except ValidationError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"


def validate_evidence_grounding(
    evidence: str,
    source_text: str,
) -> tuple[bool, str]:
    """
    Verify that an evidence string is a verbatim substring of the source text.

    This is the mechanical anti-hallucination check. It uses strict
    substring matching — no fuzzy matching, no semantic similarity,
    no normalization. If the evidence is not character-for-character
    present in the source, it fails.

    Returns:
        Tuple of (is_grounded, detail_message).
    """
    if not evidence or not evidence.strip():
        return False, "Evidence field is empty"

    if evidence in source_text:
        return True, "Evidence found verbatim in source"

    # Provide diagnostic info for near-misses (helpful for debugging,
    # but does NOT change the pass/fail result)
    evidence_stripped = evidence.strip()
    source_stripped = source_text.strip()

    # Check if it matches after whitespace normalization (still fails, but logs why)
    import re
    evidence_normalized = re.sub(r'\s+', ' ', evidence_stripped)
    source_normalized = re.sub(r'\s+', ' ', source_stripped)

    if evidence_normalized in source_normalized:
        return False, (
            "Evidence matches after whitespace normalization but NOT verbatim. "
            "The LLM likely reformatted whitespace. This is still a hallucination "
            "by our strict definition."
        )

    # Check case-insensitive (still fails)
    if evidence_stripped.lower() in source_stripped.lower():
        return False, (
            "Evidence matches case-insensitively but NOT exactly. "
            "The LLM changed capitalization."
        )

    return False, "Evidence NOT found in source text (hallucination)"


def validate_extraction_result(
    result: ExtractionResult,
    source_text: str,
) -> dict[str, Any]:
    """
    Comprehensive validation of an ExtractionResult.

    Checks:
    1. Schema validity of each parameter
    2. Evidence grounding of each parameter
    3. Consistency checks (e.g., parameters_extracted matches len(parameters))

    Returns:
        Validation report dict with detailed results.
    """
    report = {
        "source_file": result.source_file,
        "total_parameters": len(result.parameters),
        "schema_valid": 0,
        "schema_invalid": 0,
        "evidence_grounded": 0,
        "evidence_hallucinated": 0,
        "consistency_ok": True,
        "details": [],
    }

    # Check consistency
    if result.parameters_extracted != len(result.parameters):
        report["consistency_ok"] = False
        report["details"].append(
            f"Inconsistency: parameters_extracted={result.parameters_extracted} "
            f"but len(parameters)={len(result.parameters)}"
        )

    # Validate each parameter
    for param in result.parameters:
        param_report = {"name": param.name, "schema_valid": True, "evidence_grounded": True}

        # Schema is already validated by Pydantic construction, but re-check
        is_valid, error = validate_parameter_schema(param.model_dump())
        if is_valid:
            report["schema_valid"] += 1
        else:
            report["schema_invalid"] += 1
            param_report["schema_valid"] = False
            param_report["schema_error"] = error

        # Evidence grounding
        is_grounded, detail = validate_evidence_grounding(param.evidence, source_text)
        if is_grounded:
            report["evidence_grounded"] += 1
        else:
            report["evidence_hallucinated"] += 1
            param_report["evidence_grounded"] = False
            param_report["evidence_detail"] = detail

        report["details"].append(param_report)

    return report


def validate_yaml_file(yaml_path: str | Path) -> tuple[bool, str]:
    """
    Validate a YAML results file for structural correctness.

    Returns:
        Tuple of (is_valid, error_message).
    """
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        return False, f"File not found: {yaml_path}"

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            return False, "YAML file is empty"

        if not isinstance(data, (dict, list)):
            return False, f"Expected dict or list, got {type(data)}"

        return True, "YAML structure is valid"

    except yaml.YAMLError as e:
        return False, f"YAML parse error: {e}"
