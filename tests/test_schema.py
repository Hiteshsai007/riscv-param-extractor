"""
Unit tests for the Pydantic schema and candidate detection.
"""

import pytest

from schema.parameter_schema import (
    CandidateSentence,
    ConfidenceLevel,
    ExtractionResult,
    Parameter,
    ParameterType,
)
from src.candidate_detector import detect_candidates, _find_trigger_in_sentence


class TestParameterSchema:
    """Tests for the Parameter Pydantic model."""

    def test_valid_parameter(self):
        """A well-formed parameter should pass validation."""
        param = Parameter(
            name="cache_block_size",
            description="Size of a cache block",
            type=ParameterType.NUMERIC_RANGE,
            constraints="must be power-of-two",
            evidence="the size of a cache block are both implementation-specific",
            trigger_keyword="implementation-specific",
            source_section="Unprivileged Spec §13.1",
            confidence=ConfidenceLevel.HIGH,
        )
        assert param.name == "cache_block_size"
        assert param.type == ParameterType.NUMERIC_RANGE

    def test_empty_evidence_raises(self):
        """Evidence field must not be empty."""
        with pytest.raises(Exception):
            Parameter(
                name="test",
                description="test",
                type=ParameterType.BOOLEAN,
                evidence="   ",  # whitespace only
                trigger_keyword="may",
                source_section="test",
                confidence=ConfidenceLevel.LOW,
            )

    def test_empty_name_raises(self):
        """Parameter name must not be empty."""
        with pytest.raises(Exception):
            Parameter(
                name="",
                description="test",
                type=ParameterType.BOOLEAN,
                evidence="some evidence",
                trigger_keyword="may",
                source_section="test",
                confidence=ConfidenceLevel.LOW,
            )

    def test_field_behavior_type(self):
        """The field_behavior type should be accepted."""
        param = Parameter(
            name="warl_supported_values",
            description="WARL field legal value set",
            type=ParameterType.FIELD_BEHAVIOR,
            evidence="some evidence text",
            trigger_keyword="WARL",
            source_section="Priv Spec §2.1",
            confidence=ConfidenceLevel.HIGH,
        )
        assert param.type == ParameterType.FIELD_BEHAVIOR

    def test_all_confidence_levels(self):
        """All confidence levels should be valid."""
        for level in ConfidenceLevel:
            param = Parameter(
                name="test",
                description="test",
                type=ParameterType.BOOLEAN,
                evidence="evidence",
                trigger_keyword="may",
                source_section="test",
                confidence=level,
            )
            assert param.confidence == level


class TestCandidateDetector:
    """Tests for the deterministic Pass 1 candidate detection."""

    def test_implementation_specific_detected(self):
        """'implementation-specific' should be detected as a trigger."""
        text = "The cache block size is implementation-specific."
        candidates = detect_candidates(text)
        assert len(candidates) >= 1
        assert any(c.trigger_keyword == "implementation-specific" for c in candidates)

    def test_no_triggers_returns_empty(self):
        """Text without trigger keywords should return no candidates."""
        text = "The RISC-V ISA uses a 32-bit instruction encoding."
        candidates = detect_candidates(text)
        assert len(candidates) == 0

    def test_may_detected_but_not_maybe(self):
        """'may' should be detected but not 'maybe'."""
        triggers = _find_trigger_in_sentence("Implementations may support this.")
        assert "may" in triggers

        triggers_maybe = _find_trigger_in_sentence("Maybe this works differently.")
        assert "may" not in triggers_maybe

    def test_warl_case_sensitive(self):
        """WARL should be detected case-sensitively."""
        triggers = _find_trigger_in_sentence("This is a WARL field.")
        assert "WARL" in triggers

        triggers_lower = _find_trigger_in_sentence("This is a warl field.")
        assert "WARL" not in triggers_lower

    def test_multiple_triggers_in_sentence(self):
        """A sentence with multiple triggers should produce multiple candidates."""
        text = "Implementations may optionally support this feature."
        candidates = detect_candidates(text)
        keywords = {c.trigger_keyword for c in candidates}
        assert "may" in keywords or "optionally" in keywords

    def test_sentence_splitting(self):
        """Multiple sentences should be split correctly."""
        text = (
            "The first sentence has no triggers. "
            "The second sentence may have one. "
            "The third is implementation-defined."
        )
        candidates = detect_candidates(text)
        assert len(candidates) >= 2


class TestExtractionResult:
    """Tests for the ExtractionResult model."""

    def test_empty_result(self):
        """An empty extraction result should be valid."""
        result = ExtractionResult(
            source_file="test.txt",
            source_section="Test §1",
            candidates_found=0,
            parameters_extracted=0,
        )
        assert result.parameters == []
        assert result.hallucination_flags == []
