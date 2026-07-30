"""
RISC-V Architectural Parameter Schema — Source of Truth

This Pydantic model defines the contract for all extracted parameters.
Every component (extraction, validation, evaluation) depends on this schema.
Lock this BEFORE writing prompts.

Schema version: 1.0.0
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ParameterType(str, Enum):
    """Classification of the architectural parameter's variability axis."""

    BOOLEAN = "boolean"
    ENUMERATED = "enumerated"
    NUMERIC_RANGE = "numeric_range"
    FIELD_BEHAVIOR = "field_behavior"
    CAPABILITY = "capability"


class RejectionReason(str, Enum):
    """Closed set of reason codes for why a candidate was NOT classified as a parameter."""

    NOT_ISA_VISIBLE = "NOT_ISA_VISIBLE"
    CONSTRAINT_NOT_PARAMETER = "CONSTRAINT_NOT_PARAMETER"
    NOT_STATED_IN_TEXT = "NOT_STATED_IN_TEXT"
    SOFTWARE_PERMISSION = "SOFTWARE_PERMISSION"
    MANDATORY_BEHAVIOR = "MANDATORY_BEHAVIOR"
    STRUCTURAL_CONVENTION = "STRUCTURAL_CONVENTION"
    DUPLICATE = "DUPLICATE"
    MALFORMED_EVIDENCE = "MALFORMED_EVIDENCE"


class ConfidenceLevel(str, Enum):
    """Confidence that the extracted item is a genuine architectural parameter."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CandidateSentence(BaseModel):
    """Output of Pass 1: a sentence flagged by trigger keyword detection."""

    sentence: str = Field(...)
    trigger_keyword: str = Field(...)
    sentence_index: int = Field(...)


class ClassificationResult(BaseModel):
    """Output of Pass 2 classification step (before full extraction)."""

    is_parameter: bool = Field(...)
    reason: str = Field(...)
    category: Optional[str] = Field(
        default=None,
        description="If not a parameter: 'software_permission', 'mandatory_behavior', "
        "'structural_convention', or 'architectural_constant'",
    )


class Parameter(BaseModel):
    """
    A validated architectural parameter extracted from the RISC-V ISA specification.

    The `evidence` field is the critical anti-hallucination gate: it MUST be an
    exact verbatim substring of the source text. This is verified mechanically,
    not by LLM judgment.
    """

    name: str = Field(...)
    description: str = Field(...)
    type: ParameterType = Field(...)
    constraints: Optional[str] = Field(default=None)
    evidence: str = Field(...)
    trigger_keyword: str = Field(...)
    source_section: str = Field(...)
    confidence: ConfidenceLevel = Field(...)
    isa_visible: bool = Field(...)
    visibility_justification: Optional[str] = Field(default=None)

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

    @field_validator("visibility_justification")
    @classmethod
    def validate_visibility_justification(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Visibility justification is required when the parameter is ISA-visible."""
        isa_visible = info.data.get("isa_visible")
        if isa_visible is True:
            if not isinstance(v, str) or not v.strip():
                raise ValueError("visibility_justification is required when isa_visible is true")
        return v


class RejectedCandidate(BaseModel):
    """A candidate that was evaluated but NOT classified as a parameter."""

    candidate_text: str = Field(...)
    reason: RejectionReason = Field(...)
    detail: str = Field(default="")
    isa_visible: Optional[bool] = Field(default=None)
    visibility_justification: Optional[str] = Field(default=None)


class ExtractionResult(BaseModel):
    """Complete output of the extraction pipeline for a single snippet."""

    source_file: str = Field(...)
    source_section: str = Field(...)
    candidates_found: int = Field(...)
    parameters_extracted: int = Field(...)
    parameters: list[Parameter] = Field(default_factory=list)
    rejected_candidates: list[RejectedCandidate] = Field(default_factory=list)
    hallucination_flags: list[str] = Field(default_factory=list)
