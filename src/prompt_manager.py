"""
Prompt Manager — Loads and formats versioned prompts for the extraction pipeline.

Prompts are stored as markdown files in the prompts/ directory. This module
loads them and formats them with runtime context (the actual snippet text,
candidate sentences, schema definition, etc.).

Design: System prompt contains role definition, schema, rules, and few-shot examples.
        User prompt contains only the snippet to process.
        This separation matters because system prompts receive higher attention weight
        in most instruction-tuned models.
"""

import json
from pathlib import Path

from schema.parameter_schema import CandidateSentence, ParameterType


# Root directory for prompt files
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _get_schema_description() -> str:
    """Generate a human-readable schema description for the LLM."""
    type_values = [t.value for t in ParameterType]
    return f"""Output Schema (YAML format, strict compliance required):
- name: string (lowercase, underscore-separated identifier, e.g., "cache_block_size")
- description: string (1-2 sentences explaining what varies across implementations)
- type: one of {type_values}
- constraints: string or null (any constraints on valid values)
- evidence: string (EXACT VERBATIM substring from the source text — character-for-character match required)
- trigger_keyword: string (the keyword that flagged this text)
- source_section: string (chapter/section id from the ISA manual)
- confidence: one of ["high", "medium", "low"]"""


def load_prompt(version: str) -> dict[str, str]:
    """
    Load a prompt version from the prompts/ directory.

    Args:
        version: Prompt version identifier (e.g., "v1_baseline").
                 Must correspond to a file in prompts/{version}.md

    Returns:
        Dict with 'system' and 'user_template' keys containing the prompt text.
        The user_template contains {snippet} and {candidates} placeholders.

    Raises:
        FileNotFoundError: If the prompt version file doesn't exist.
    """
    prompt_path = PROMPTS_DIR / f"{version}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt version '{version}' not found at {prompt_path}. "
            f"Available versions: {[p.stem for p in PROMPTS_DIR.glob('v*.md')]}"
        )

    content = prompt_path.read_text(encoding="utf-8")

    # Prompts are structured with --- separators:
    # Section 1: System prompt
    # Section 2: User prompt template
    sections = content.split("---USER_PROMPT---")

    if len(sections) != 2:
        raise ValueError(
            f"Prompt file {prompt_path} must contain exactly one '---USER_PROMPT---' "
            f"separator dividing system prompt from user prompt template. "
            f"Found {len(sections) - 1} separators."
        )

    system_prompt = sections[0].strip()
    user_template = sections[1].strip()

    return {
        "system": system_prompt,
        "user_template": user_template,
    }


def format_user_prompt(
    template: str,
    snippet: str,
    candidates: list[CandidateSentence],
    source_section: str,
) -> str:
    """
    Format the user prompt template with runtime context.

    Args:
        template: User prompt template with placeholders.
        snippet: Raw text snippet from the ISA manual.
        candidates: List of candidate sentences from Pass 1.
        source_section: Chapter/section identifier.

    Returns:
        Formatted user prompt string ready to send to the LLM.
    """
    # Format candidates as a numbered list
    candidates_text = ""
    if candidates:
        lines = []
        for i, c in enumerate(candidates, 1):
            lines.append(
                f"{i}. [Trigger: \"{c.trigger_keyword}\"] {c.sentence}"
            )
        candidates_text = "\n".join(lines)
    else:
        candidates_text = "(No trigger-keyword candidates detected)"

    formatted = template.replace("{snippet}", snippet)
    formatted = formatted.replace("{candidates}", candidates_text)
    formatted = formatted.replace("{source_section}", source_section)
    formatted = formatted.replace("{schema}", _get_schema_description())

    return formatted


def get_system_prompt(version: str) -> str:
    """Convenience: load and return just the system prompt for a version."""
    prompts = load_prompt(version)
    return prompts["system"]


def get_formatted_prompt(
    version: str,
    snippet: str,
    candidates: list[CandidateSentence],
    source_section: str,
) -> dict[str, str]:
    """
    Load a prompt version and format it with runtime context.

    Returns:
        Dict with 'system' and 'user' keys containing ready-to-send prompts.
    """
    prompts = load_prompt(version)
    user_prompt = format_user_prompt(
        prompts["user_template"],
        snippet=snippet,
        candidates=candidates,
        source_section=source_section,
    )

    return {
        "system": prompts["system"],
        "user": user_prompt,
    }
