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
)
from src.candidate_detector import detect_candidates
from src.llm_client import GenerationConfig, LLMClient, LLMResponse
from src.prompt_manager import get_formatted_prompt

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


def _parse_yaml_from_response(response_text: str) -> list[dict[str, Any]]:
    """
    Extract and parse YAML from the LLM response.

    The LLM may wrap YAML in markdown code fences or include preamble text.
    This function handles both cases.
    """
    # Try to extract YAML from markdown code fences
    yaml_match = re.search(
        r'```(?:yaml|YAML)?\s*\n(.*?)```',
        response_text,
        re.DOTALL,
    )

    if yaml_match:
        yaml_text = yaml_match.group(1).strip()
    else:
        # Try the whole response as YAML
        yaml_text = response_text.strip()

    if not yaml_text or yaml_text.lower() in ("none", "null", "[]", "no parameters found"):
        return []

    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        logger.warning("YAML parse error: %s", e)
        raise ValueError(f"Failed to parse YAML from LLM response: {e}") from e

    # Normalize to list
    if parsed is None:
        return []
    if isinstance(parsed, dict):
        # Single parameter returned as dict
        return [parsed]
    if isinstance(parsed, list):
        return parsed

    raise ValueError(f"Unexpected YAML structure: {type(parsed)}")


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

            parsed_params = _parse_yaml_from_response(raw_response.content)
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

    if not parsed_params and last_error:
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

    for param_dict in parsed_params:
        try:
            # Pydantic schema validation
            param = Parameter(**param_dict)

            # Evidence grounding check (the critical anti-hallucination gate)
            if _validate_evidence(param, snippet_text):
                validated_params.append(param)
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
            logger.warning(
                "Schema validation failed for parameter: %s — Error: %s",
                param_dict.get("name", "UNKNOWN"),
                e,
            )
            hallucination_flags.append(
                f"SCHEMA_INVALID: {param_dict.get('name', 'UNKNOWN')} — {e}"
            )

    logger.info(
        "Extraction complete: %d validated, %d hallucination flags",
        len(validated_params),
        len(hallucination_flags),
    )

    return ExtractionResult(
        source_file=source_file,
        source_section=source_section,
        candidates_found=len(candidates),
        parameters_extracted=len(validated_params),
        parameters=validated_params,
        rejected_candidates=[],
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
