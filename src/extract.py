"""
Main Extraction Pipeline — Orchestrates Pass 1 + Pass 2.

This is the core module that:
1. Runs Pass 1 (deterministic candidate detection)
2. Runs Pass 2 (LLM-based classification + extraction)
3. Validates output (schema + evidence grounding)
4. Produces structured ExtractionResult

Error handling strategy:
- Malformed LLM output → retry up to max_retries
- Empty extraction → valid "no parameters found" result
- Evidence check failure → flag as hallucination, include in output
- LLM timeout/API error → retry with delay, log and skip on final failure
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from schema.parameter_schema import (
    CandidateSentence,
    ExtractionResult,
    Parameter,
    RejectedCandidate,
)
from src.candidate_detector import detect_candidates
from src.llm_client import GenerationConfig, LLMClient, LLMResponse
from src.prompt_manager import get_formatted_prompt
from src.validate_yaml import validate_evidence_heuristics
from src.isa_verification import justification_cites_real_mnemonic

logger = logging.getLogger(__name__)


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load pipeline configuration from YAML file."""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _create_client_from_config(config: dict[str, Any]) -> LLMClient:
    """Create an LLM client from configuration dict."""
    model_config = config.get("model", {})
    gen_config = config.get("generation", {})

    return LLMClient(
        provider=model_config.get("provider", "ollama"),
        model_name=model_config.get("name", "qwen2.5:7b-instruct"),
        base_url=model_config.get("base_url", "http://localhost:11434"),
        api_key=model_config.get("api_key"),
        generation_config=GenerationConfig(
            temperature=gen_config.get("temperature", 0.0),
            top_p=gen_config.get("top_p", 1.0),
            repetition_penalty=gen_config.get("repetition_penalty", 1.0),
            max_tokens=gen_config.get("max_tokens", 4096),
            seed=gen_config.get("seed", 42),
            num_ctx=gen_config.get("num_ctx", 8192),
        ),
    )


def enforce_isa_visibility_gate(param_dict: dict) -> tuple[bool, str | None]:
    """
    Returns (allowed, rejection_reason). Runs regardless of what the LLM claimed.
    """
    # All failures intentionally collapse to NOT_ISA_VISIBLE: an item is not
    # admissible unless the model both claims visibility and supplies a
    # substantive, independently verifiable ISA citation.
    if param_dict.get("isa_visible") is not True:
        return False, "NOT_ISA_VISIBLE"

    justification = param_dict.get("visibility_justification", "")
    if len(justification.strip()) < 20:
        return False, "NOT_ISA_VISIBLE"
    if not justification_cites_real_mnemonic(justification):
        return False, "NOT_ISA_VISIBLE"
    # Extra strict rule for CMO/cache snippets (live failure observed 2026-07-30)
    if "cache" in param_dict.get("name", "").lower() and "CBO." not in justification.upper():
        return False, "NOT_ISA_VISIBLE"
    return True, None


def _parse_yaml_from_response(response_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract and parse YAML from the LLM response.

    Supports MULTIPLE fenced YAML blocks (the model may emit two or more
    separate ```yaml blocks). All valid items across blocks are merged.
    """
    # Fast path for empty array
    cleaned = re.sub(r'```(?:yaml|YAML)?|```', '', response_text)
    if cleaned.strip() in ("[]", "") and "- name:" not in response_text:
        return [], []

    # Collect ALL fenced YAML blocks (supports multiple ```yaml ... ```)
    fence_pattern = re.compile(
        r'```(?:yaml|YAML)?\s*\n(.*?)\n```', re.DOTALL | re.IGNORECASE
    )
    fenced_blocks = fence_pattern.findall(response_text)

    # Also treat the whole response as one block if no fences but contains YAML list items
    if not fenced_blocks:
        if re.search(r'^\s*-\s+(name|candidate_text):', response_text, re.MULTILINE):
            fenced_blocks = [response_text]
        else:
            return [], []

    all_params: list[dict[str, Any]] = []
    all_rejections: list[dict[str, Any]] = []

    for block in fenced_blocks:
        block = block.strip()
        if not block or block.lower() in ("none", "null", "[]"):
            continue

        # Skip thought_process blocks
        if block.startswith("<thought_process>"):
            continue

        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError:
            continue

        if parsed is None:
            continue

        if isinstance(parsed, dict):
            if "parameters" in parsed or "rejected_candidates" in parsed:
                all_params.extend(parsed.get("parameters") or [])
                all_rejections.extend(parsed.get("rejected_candidates") or [])
            else:
                # single dict item
                if "candidate_text" in parsed and "reason" in parsed:
                    all_rejections.append(parsed)
                else:
                    all_params.append(parsed)
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    if "candidate_text" in item and "reason" in item:
                        all_rejections.append(item)
                    else:
                        all_params.append(item)

    # Deduplicate by name (keep first occurrence)
    seen_names = set()
    deduped_params = []
    for p in all_params:
        name = p.get("name") if isinstance(p, dict) else None
        if name and name not in seen_names:
            seen_names.add(name)
            deduped_params.append(p)
        elif not name:
            deduped_params.append(p)

    return deduped_params, all_rejections


def _validate_evidence(parameter: Parameter, source_text: str) -> bool:
    """
    Verify that the parameter's evidence field is a verbatim substring
    of the source text.

    This is the critical anti-hallucination gate. It is mechanical,
    requires no LLM call, and is the cheapest high-value check in
    the pipeline.
    """
    return parameter.evidence in source_text


def extract_from_snippet(
    snippet_text: str,
    source_section: str,
    source_file: str,
    config: dict[str, Any],
    client: LLMClient | None = None,
) -> ExtractionResult:
    """
    Run the full extraction pipeline on a single text snippet.

    Args:
        snippet_text: Raw text from the ISA manual.
        source_section: Chapter/section identifier (e.g., "Privileged Spec §2.1").
        source_file: Path to the input file (for logging).
        config: Pipeline configuration dict.
        client: Optional pre-created LLM client (for reuse across snippets).

    Returns:
        ExtractionResult with validated parameters, rejected candidates,
        and hallucination flags.
    """
    pipeline_config = config.get("pipeline", {})
    prompt_version = config.get("prompt", {}).get("version", "v1_baseline")
    max_retries = pipeline_config.get("max_retries", 2)
    retry_delay = pipeline_config.get("retry_delay_seconds", 1)

    # --- Pass 1: Deterministic candidate detection ---
    logger.info("Pass 1: Detecting candidates in '%s'", source_file)
    candidates = detect_candidates(snippet_text)
    logger.info("Pass 1 complete: %d candidates found", len(candidates))

    if not candidates:
        logger.info("No candidates found — returning empty result")
        return ExtractionResult(
            source_file=source_file,
            source_section=source_section,
            candidates_found=0,
            parameters_extracted=0,
            parameters=[],
            rejected_candidates=[],
            hallucination_flags=[],
        )

    # --- Pass 2: LLM classification + extraction ---
    if client is None:
        client = _create_client_from_config(config)

    # Build the prompt
    prompts = get_formatted_prompt(
        version=prompt_version,
        snippet=snippet_text,
        candidates=candidates,
        source_section=source_section,
    )

    # Call LLM with retry logic
    raw_response: LLMResponse | None = None
    parsed_params: list[dict[str, Any]] = []
    parsed_rejections: list[dict[str, Any]] = []
    last_error: str = ""

    for attempt in range(max_retries + 1):
        try:
            logger.info(
                "Pass 2: Calling LLM (attempt %d/%d)",
                attempt + 1,
                max_retries + 1,
            )
            raw_response = client.chat(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
            )

            logger.debug("Raw LLM response:\n%s", raw_response.content)

            parsed_params, parsed_rejections = _parse_yaml_from_response(raw_response.content)
            break  # Success — exit retry loop

        except (ValueError, yaml.YAMLError) as e:
            last_error = str(e)
            logger.warning(
                "Attempt %d failed (parse error): %s",
                attempt + 1,
                last_error,
            )
            if attempt < max_retries:
                time.sleep(retry_delay)
            continue

        except Exception as e:
            last_error = str(e)
            logger.error(
                "Attempt %d failed (unexpected error): %s",
                attempt + 1,
                last_error,
            )
            if attempt < max_retries:
                time.sleep(retry_delay)
            continue

    if not parsed_params and not parsed_rejections and last_error:
        logger.error(
            "All %d attempts failed for '%s'. Last error: %s",
            max_retries + 1,
            source_file,
            last_error,
        )
        # Return result with zero extractions but log the failure
        return ExtractionResult(
            source_file=source_file,
            source_section=source_section,
            candidates_found=len(candidates),
            parameters_extracted=0,
            parameters=[],
            rejected_candidates=[],
            hallucination_flags=[f"LLM_FAILURE: {last_error}"],
        )

    # --- Validation: Schema + Evidence grounding ---
    validated_params: list[Parameter] = []
    hallucination_flags: list[str] = []

    for param_dict in parsed_params.copy():
        try:
            if not isinstance(param_dict, dict):
                raise TypeError(f"Expected dict for parameter, got {type(param_dict).__name__}: {param_dict}")
                
            # T0.1: Enforce ISA visibility mechanically before trusting the LLM
            is_valid, reason = enforce_isa_visibility_gate(param_dict)
            if not is_valid:
                # Morph this into a rejected candidate dict and skip
                parsed_rejections.append({
                    "candidate_text": param_dict.get("evidence", "UNKNOWN"),
                    "reason": reason,
                    "justification": param_dict.get("visibility_justification") or param_dict.get("description", "Automatically rejected by ISA-visibility gate.")
                })
                parsed_params.remove(param_dict)
                continue

            # Pydantic schema validation
            param = Parameter(**param_dict)

            # Evidence grounding check (the critical anti-hallucination gate)
            if _validate_evidence(param, snippet_text):
                validated_params.append(param)
                
                # R3: Secondary heuristic checks (ellipses, mid-clause)
                heuristics_warnings = validate_evidence_heuristics(param.evidence, snippet_text)
                for warning in heuristics_warnings:
                    hallucination_flags.append(f"HEURISTIC_WARNING: Parameter '{param.name}' — {warning}")
            else:
                hallucination_flags.append(
                    f"EVIDENCE_MISMATCH: Parameter '{param.name}' — "
                    f"evidence not found verbatim in source: "
                    f"\"{param.evidence[:100]}...\""
                )
                logger.warning(
                    "Hallucination detected: evidence for '%s' not found in source",
                    param.name,
                )

        except Exception as e:
            param_name = param_dict.get("name", "UNKNOWN") if isinstance(param_dict, dict) else "UNKNOWN"
            logger.warning(
                "Schema validation failed for parameter: %s — Error: %s",
                param_name,
                e,
            )
            hallucination_flags.append(
                f"SCHEMA_INVALID: {param_name} — {e}"
            )

    # Validate and populate rejected candidates
    validated_rejections: list[RejectedCandidate] = []
    for rej_dict in parsed_rejections:
        try:
            if not isinstance(rej_dict, dict):
                continue
            validated_rejections.append(RejectedCandidate(**rej_dict))
        except Exception as e:
            cand_text = rej_dict.get("candidate_text", "UNKNOWN") if isinstance(rej_dict, dict) else "UNKNOWN"
            logger.warning("Schema validation failed for rejected candidate: %s — Error: %s", cand_text, e)

    logger.info(
        "Extraction complete: %d validated, %d rejections, %d hallucination flags",
        len(validated_params),
        len(validated_rejections),
        len(hallucination_flags),
    )

    return ExtractionResult(
        source_file=source_file,
        source_section=source_section,
        candidates_found=len(candidates),
        parameters_extracted=len(validated_params),
        parameters=validated_params,
        rejected_candidates=validated_rejections,
        hallucination_flags=hallucination_flags,
    )


def create_run_manifest(
    config: dict[str, Any],
    input_files: list[str],
    output_dir: str,
) -> dict[str, Any]:
    """
    Generate a run manifest recording all configuration for reproducibility.

    Every output file can be traced back to exact parameters via this manifest.
    """
    return {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": config.get("model", {}),
        "generation": config.get("generation", {}),
        "pipeline": config.get("pipeline", {}),
        "prompt_version": config.get("prompt", {}).get("version", "unknown"),
        "input_files": input_files,
        "output_dir": output_dir,
    }
