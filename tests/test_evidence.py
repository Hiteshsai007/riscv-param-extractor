"""
Unit tests for evidence grounding validation.
"""

import pytest

from src.validate_yaml import validate_evidence_grounding, validate_parameter_schema


class TestEvidenceGrounding:
    """Tests for the verbatim substring evidence check."""

    def test_exact_match_passes(self):
        """Verbatim substring should pass."""
        evidence = "the size of a cache block are both implementation-specific"
        source = (
            "The capacity and organization of a cache and "
            "the size of a cache block are both implementation-specific, "
            "and the execution environment provides software a means."
        )
        is_grounded, _ = validate_evidence_grounding(evidence, source)
        assert is_grounded is True

    def test_paraphrase_fails(self):
        """Paraphrased evidence should fail."""
        evidence = "cache block sizes are implementation-specific"
        source = (
            "The capacity and organization of a cache and "
            "the size of a cache block are both implementation-specific."
        )
        is_grounded, _ = validate_evidence_grounding(evidence, source)
        assert is_grounded is False

    def test_case_mismatch_fails(self):
        """Case-changed evidence should fail (strict check)."""
        evidence = "The Size of a Cache Block"
        source = "the size of a cache block"
        is_grounded, detail = validate_evidence_grounding(evidence, source)
        assert is_grounded is False
        assert "case-insensitively" in detail

    def test_whitespace_mismatch_fails(self):
        """Whitespace-normalized evidence should still fail."""
        evidence = "the  size  of  a  cache  block"
        source = "the size of a cache block"
        is_grounded, detail = validate_evidence_grounding(evidence, source)
        assert is_grounded is False
        assert "whitespace normalization" in detail

    def test_empty_evidence_fails(self):
        """Empty evidence should fail."""
        is_grounded, detail = validate_evidence_grounding("", "some source text")
        assert is_grounded is False
        assert "empty" in detail.lower()

    def test_whitespace_only_evidence_fails(self):
        """Whitespace-only evidence should fail."""
        is_grounded, detail = validate_evidence_grounding("   ", "some source text")
        assert is_grounded is False


class TestSchemaValidation:
    """Tests for parameter schema validation."""

    def test_valid_parameter_dict(self):
        """A valid parameter dict should pass schema validation."""
        param = {
            "name": "cache_block_size",
            "description": "Size of cache block",
            "type": "numeric_range",
            "evidence": "implementation-specific",
            "trigger_keyword": "implementation-specific",
            "source_section": "Spec §1",
            "confidence": "high",
        }
        is_valid, error = validate_parameter_schema(param)
        assert is_valid is True
        assert error == ""

    def test_missing_required_field_fails(self):
        """Missing required fields should fail validation."""
        param = {
            "name": "test",
            "description": "test",
            # missing type, evidence, etc.
        }
        is_valid, error = validate_parameter_schema(param)
        assert is_valid is False

    def test_invalid_type_value_fails(self):
        """Invalid type enum value should fail validation."""
        param = {
            "name": "test",
            "description": "test",
            "type": "invalid_type",
            "evidence": "evidence",
            "trigger_keyword": "may",
            "source_section": "test",
            "confidence": "high",
        }
        is_valid, error = validate_parameter_schema(param)
        assert is_valid is False
