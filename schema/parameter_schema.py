"""
RISC-V Architectural Parameter Schema — Source of Truth

This Pydantic model defines the contract for all extracted parameters.
Every component (extraction, validation, evaluation) depends on this schema.
Lock this BEFORE writing prompts.

Schema version: 1.0.0
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ParameterType(str, Enum):
    """Classification of the architectural parameter's variability axis."""

    BOOLEAN = "boolean"  # Implementation either supports or doesn't (e.g., optional extension)
    ENUMERATED = "enumerated"  # Implementation chooses from a set of legal values (e.g., WLRL fields)
    NUMERIC_RANGE = "numeric_range"  # Implementation chooses a value within a range (e.g., cache block size)
    FIELD_BEHAVIOR = "field_behavior"  # CSR field behavior class (WPRI, WLRL, WARL)
    CAPABILITY = "capability"  # Optional hardware capability (e.g., trap-and-emulate)


class ConfidenceLevel(str, Enum):
    """Confidence that the extracted item is a genuine architectural parameter."""

    HIGH = "high"  # Clear implementation-variability language with explicit axis
    MEDIUM = "medium"  # Likely parameter but language is somewhat ambiguous
    LOW = "low"  # Possible parameter; borderline case


class CandidateSentence(BaseModel):
    """Output of Pass 1: a sentence flagged by trigger keyword detection."""

    sentence: str = Field(
        ...,
        description="The full sentence containing the trigger keyword",
    )
    trigger_keyword: str = Field(
        ...,
        description="The specific keyword that triggered detection "
        "(e.g., 'may', 'implementation-defined')",
    )
    sentence_index: int = Field(
        ...,
        description="0-based index of this sentence within the source snippet",
    )


class ClassificationResult(BaseModel):
    """Output of Pass 2 classification step (before full extraction)."""

    is_parameter: bool = Field(
        ...,
        description="True if this candidate describes genuine hardware implementation variability",
    )
    reason: str = Field(
        ...,
        description="Brief explanation of classification decision",
    )
    category: Optional[str] = Field(
        default=None,
        description="If not a parameter: 'software_permission', 'mandatory_behavior', "
        "'structural_convention', or 'architectural_constant'",
    )


class Parameter(BaseModel):
    """
    A validated architectural parameter extracted from the RISC-V ISA specification.

    This is the primary output schema. The `evidence` field is the critical
    anti-hallucination gate: it MUST be an exact verbatim substring of the
    source text. This is verified mechanically, not by LLM judgment.
    """

    name: str = Field(
        ...,
        description="Concise, descriptive name for the parameter "
        "(e.g., 'cache_block_size', 'misa_warl_behavior')",
    )
    description: str = Field(
        ...,
        description="One-to-two sentence description of what this parameter controls "
        "and how implementations may vary",
    )
    type: ParameterType = Field(
        ...,
        description="Classification of the parameter's variability axis",
    )
    constraints: Optional[str] = Field(
        default=None,
        description="Any constraints on valid values (e.g., 'must be power-of-two', "
        "'minimum 4 bytes')",
    )
    evidence: str = Field(
        ...,
        description="VERBATIM substring from the source text that proves this is "
        "an implementation-variable parameter. Must be an exact character-for-character "
        "match against the input snippet.",
    )
    trigger_keyword: str = Field(
        ...,
        description="The linguistic signal that flagged this text "
        "(e.g., 'may', 'implementation-defined', 'optional')",
    )
    source_section: str = Field(
        ...,
        description="Chapter/section identifier from the ISA manual "
        "(e.g., 'Privileged Spec §2.1', 'Unprivileged Spec §13.1')",
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Confidence that this is a genuine architectural parameter",
    )

    @field_validator("evidence")
    @classmethod
    def evidence_must_not_be_empty(cls, v: str) -> str:
        """Evidence field cannot be empty or whitespace-only."""
        if not v.strip():
            raise ValueError("Evidence field must contain non-whitespace text")
        return v

    @field_validator("name")
    @classmethod
    def name_must_be_identifier_like(cls, v: str) -> str:
        """Parameter names should be lowercase, underscore-separated identifiers."""
        if not v.strip():
            raise ValueError("Parameter name cannot be empty")
        return v.strip()


class ExtractionResult(BaseModel):
    """Complete output of the extraction pipeline for a single snippet."""

    source_file: str = Field(
        ...,
        description="Path to the input snippet file",
    )
    source_section: str = Field(
        ...,
        description="Chapter/section identifier from the ISA manual",
    )
    candidates_found: int = Field(
        ...,
        description="Number of candidate sentences identified in Pass 1",
    )
    parameters_extracted: int = Field(
        ...,
        description="Number of validated parameters extracted in Pass 2",
    )
    parameters: list[Parameter] = Field(
        default_factory=list,
        description="List of extracted and validated parameters",
    )
    rejected_candidates: list[ClassificationResult] = Field(
        default_factory=list,
        description="Candidates classified as non-parameters with reasons",
    )
    hallucination_flags: list[str] = Field(
        default_factory=list,
        description="List of evidence strings that failed verbatim substring check",
    )
