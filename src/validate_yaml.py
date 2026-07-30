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
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from schema.parameter_schema import ExtractionResult, Parameter, RejectedCandidate, RejectionReason

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


def _normalize_whitespace(text: str) -> str:
    """Collapse whitespace runs to a single space for mechanical comparison."""
    return re.sub(r"\s+", " ", text or "").strip()


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

    normalized_evidence = _normalize_whitespace(evidence)
    normalized_source = _normalize_whitespace(source_text)

    if not normalized_evidence:
        return False, "Evidence field is empty"

    if evidence in source_text:
        return True, "Evidence found verbatim in source"

    if normalized_evidence in normalized_source:
        return False, (
            "Evidence matches after whitespace normalization but NOT verbatim. "
            "The LLM likely reformatted whitespace. This is still a hallucination "
            "by our strict definition."
        )

    if evidence.strip().lower() in source_text.lower():
        return False, (
            "Evidence matches case-insensitively but NOT exactly. "
            "The LLM changed capitalization or punctuation."
        )

    return False, "Evidence NOT found in source text (hallucination)"


def validate_evidence_heuristics(
    evidence: str,
    source_text: str,
) -> list[str]:
    """
    Apply secondary heuristic checks on evidence strings beyond
    the verbatim substring match.

    Returns:
        List of warning strings. Empty list = all checks passed.
    """
    warnings = []

    # Ban ellipses outright — if a quote needs an ellipsis, it isn't clean grounding
    if "..." in evidence or "…" in evidence:
        warnings.append(
            "ELLIPSIS_IN_EVIDENCE: Evidence contains '...' or '…'. "
            "Ellipses indicate a truncated quote that may omit qualifying context."
        )

    # Reject evidence that starts mid-clause on a lowercase word directly
    # following a conjunction (and, or, but) in the source text.
    evidence_stripped = evidence.strip()
    if evidence_stripped and evidence_stripped[0].islower():
        # Find where this evidence appears in the source
        idx = source_text.find(evidence_stripped)
        if idx > 0:
            # Look at what comes immediately before the evidence in the source
            preceding = source_text[:idx].rstrip()
            if preceding:
                last_word = preceding.split()[-1].rstrip(".,;:").lower()
                if last_word in ("and", "or", "but"):
                    warnings.append(
                        f"MID_CLAUSE_EVIDENCE: Evidence starts mid-clause after "
                        f"conjunction '{last_word}'. The full source sentence may "
                        f"change the meaning of this fragment."
                    )

    return warnings


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
        "rejected_candidates_valid": True,
        "details": [],
    }

    # Check consistency
    if result.parameters_extracted != len(result.parameters):
        report["consistency_ok"] = False
        report["details"].append(
            f"Inconsistency: parameters_extracted={result.parameters_extracted} "
            f"but len(parameters)={len(result.parameters)}"
        )

    for param in result.parameters:
        param_report = {"name": param.name, "schema_valid": True, "evidence_grounded": True}

        is_valid, error = validate_parameter_schema(param.model_dump())
        if is_valid:
            report["schema_valid"] += 1
        else:
            report["schema_invalid"] += 1
            param_report["schema_valid"] = False
            param_report["schema_error"] = error

        is_grounded, detail = validate_evidence_grounding(param.evidence, source_text)
        if is_grounded:
            report["evidence_grounded"] += 1
        else:
            report["evidence_hallucinated"] += 1
            param_report["evidence_grounded"] = False
            param_report["evidence_detail"] = detail

        if param.isa_visible and not param.visibility_justification:
            report["details"].append({**param_report, "isa_visibility_error": "Missing visibility justification"})
            report["rejected_candidates_valid"] = False
        elif param.isa_visible and not re.search(r"\b(?:ADD|CBO\.ZERO|CBO\.CLEAN|CBO\.FLUSH|CBO\.INVAL|CSRRS|CSRRW|CSRRWI|CSRRC|CSRRCI|MRET|SRET|ECALL|EBREAK|FENCE|SFENCE|VSETVLI|MARCHID|MIMPID|MVENDORID|MHPMCOUNTER3|PMPADDR|PMPCFG)\b", param.visibility_justification or "", re.IGNORECASE):
            report["details"].append({**param_report, "isa_visibility_error": "Visibility justification did not cite a real mnemonic"})
            report["rejected_candidates_valid"] = False

        report["details"].append(param_report)

    for rejected in result.rejected_candidates:
        try:
            RejectedCandidate(**rejected.model_dump() if hasattr(rejected, 'model_dump') else rejected)
        except ValidationError:
            report["rejected_candidates_valid"] = False
            break
        if hasattr(rejected, 'reason'):
            try:
                RejectionReason(rejected.reason)
            except ValueError:
                report["rejected_candidates_valid"] = False
                break

    report["evidence_heuristic_warnings"] = []
    for param in result.parameters:
        heuristic_warnings = validate_evidence_heuristics(param.evidence, source_text)
        for w in heuristic_warnings:
            report["evidence_heuristic_warnings"].append(
                f"{param.name}: {w}"
            )

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

        if not isinstance(data, dict):
            return False, f"Expected mapping with schema fields, got {type(data)}"

        if not all(k in data for k in ["source_file", "source_section", "candidates_found", "parameters_extracted", "parameters", "rejected_candidates", "hallucination_flags"]):
            return False, "Missing required extraction result fields"

        if not isinstance(data.get("parameters"), list):
            return False, "parameters must be a list"
        if not isinstance(data.get("rejected_candidates"), list):
            return False, "rejected_candidates must be a list"
        if not isinstance(data.get("hallucination_flags"), list):
            return False, "hallucination_flags must be a list"

        for param in data.get("parameters", []):
            if not isinstance(param, dict):
                return False, "Each parameter must be a mapping"
            required = ["name", "description", "type", "constraints", "evidence", "trigger_keyword", "source_section", "confidence", "isa_visible", "visibility_justification"]
            missing = [field for field in required if field not in param]
            if missing:
                return False, f"Parameter missing fields: {missing}"
            if not isinstance(param.get("name"), str) or not param.get("name").strip():
                return False, "Parameter name must be a non-empty string"
            if not isinstance(param.get("description"), str) or not param.get("description").strip():
                return False, "Parameter description must be a non-empty string"
            if not isinstance(param.get("evidence"), str) or not param.get("evidence").strip():
                return False, "Parameter evidence must be a non-empty string"
            if not isinstance(param.get("isa_visible"), bool):
                return False, "Parameter isa_visible must be a bool"
            if param.get("isa_visible") is True and (not isinstance(param.get("visibility_justification"), str) or not param.get("visibility_justification", "").strip()):
                return False, "isa_visible=true requires visibility_justification"

            source_hint = data.get("source_file")
            source_path = None
            if isinstance(source_hint, str):
                source_path = Path(source_hint)
                if not source_path.is_absolute():
                    candidate_paths = [Path.cwd() / source_path, Path.cwd() / "data" / "raw_snippets" / source_path.name, Path.cwd() / "tests" / "bad_examples" / source_path.name]
                    for candidate in candidate_paths:
                        if candidate.exists():
                            source_path = candidate
                            break
            if source_path is None or not source_path.exists():
                return False, f"Source snippet not found for {data.get('source_file')}"
            source_text = source_path.read_text(encoding="utf-8")
            is_grounded, detail = validate_evidence_grounding(param.get("evidence"), source_text)
            if not is_grounded:
                return False, f"Evidence grounding failed: {detail}"

        for rejection in data.get("rejected_candidates", []):
            if not isinstance(rejection, dict):
                return False, "Each rejected candidate must be a mapping"
            if "reason" not in rejection:
                return False, "Rejected candidate must include a reason"
            try:
                RejectionReason(rejection["reason"])
            except ValueError:
                return False, f"Rejected reason {rejection['reason']} is not allowed"

        return True, "YAML structure is valid"

    except yaml.YAMLError as e:
        return False, f"YAML parse error: {e}"
