"""
Regression tests for epistemic rigor requirements (R1, R2, R6).

R1: ISA-visibility gate — cache_capacity_and_organization must be rejected
R2: Rejection reason codes — closed enum, structured output
R6: Evidence heuristic checks — ellipsis ban, mid-clause detection
"""

import pytest

from schema.parameter_schema import (
    Parameter,
    RejectedCandidate,
    RejectionReason,
    ExtractionResult,
)
from src.validate_yaml import validate_evidence_heuristics


# ──────────────────────────────────────────────────────────────────────
# R1: ISA-Visibility Gate
# ──────────────────────────────────────────────────────────────────────

class TestISAVisibilityGate:
    """
    Pin the canonical bug: cache_capacity_and_organization is NOT ISA-visible.
    This is the exact case the prior pipeline got wrong — it must never silently regress.
    """

    def test_cache_capacity_rejected_as_not_isa_visible(self):
        """cache_capacity_and_organization should be rejected with NOT_ISA_VISIBLE."""
        rejection = RejectedCandidate(
            candidate_text="The capacity and organization of a cache",
            reason=RejectionReason.NOT_ISA_VISIBLE,
            detail=(
                "Cache capacity and organization are microarchitectural details. "
                "No ISA-defined instruction produces different specified behavior "
                "based on cache capacity."
            ),
            isa_visible=False,
            visibility_justification=(
                "No RISC-V instruction's architecturally-defined behavior depends "
                "on cache capacity or internal organization."
            ),
        )
        assert rejection.reason == RejectionReason.NOT_ISA_VISIBLE
        assert rejection.isa_visible is False

    def test_cache_block_size_accepted_as_isa_visible(self):
        """cache_block_size IS ISA-visible (CMO instructions depend on it)."""
        param = Parameter(
            name="cache_block_size",
            description="The size of a cache block.",
            type="numeric_range",
            evidence="the size of a cache block are both implementation-specific",
            trigger_keyword="implementation-specific",
            source_section="Unprivileged Spec, CMO §cmo",
            confidence="high",
            isa_visible=True,
            visibility_justification=(
                "CMO instructions operate on cache-block-sized granules."
            ),
        )
        assert param.isa_visible is True
        assert "CMO" in param.visibility_justification

    def test_parameter_schema_accepts_isa_visible_fields(self):
        """Parameter model should accept the new isa_visible fields."""
        param = Parameter(
            name="test_param",
            description="Test",
            type="boolean",
            evidence="test evidence",
            trigger_keyword="may",
            source_section="Test §1",
            confidence="high",
            isa_visible=True,
            visibility_justification="Test justification",
        )
        assert param.isa_visible is True

    def test_parameter_schema_backwards_compatible(self):
        """Parameter model should still work WITHOUT isa_visible (backwards compat)."""
        param = Parameter(
            name="test_param",
            description="Test",
            type="boolean",
            evidence="test evidence",
            trigger_keyword="may",
            source_section="Test §1",
            confidence="high",
        )
        assert param.isa_visible is None


# ──────────────────────────────────────────────────────────────────────
# R2: Rejection Reason Codes
# ──────────────────────────────────────────────────────────────────────

class TestRejectionReasonCodes:
    """Test the closed rejection reason enum and RejectedCandidate model."""

    def test_all_reason_codes_exist(self):
        """All 5 defined reason codes should be in the enum."""
        expected = {
            "NOT_ISA_VISIBLE",
            "CONSTRAINT_NOT_PARAMETER",
            "NOT_STATED_IN_TEXT",
            "DUPLICATE",
            "MALFORMED_EVIDENCE",
        }
        actual = {r.value for r in RejectionReason}
        assert expected == actual

    def test_rejected_candidate_requires_reason(self):
        """RejectedCandidate must have a reason code."""
        with pytest.raises(Exception):
            RejectedCandidate(candidate_text="test")

    def test_rejected_candidate_invalid_reason_fails(self):
        """Invalid reason code should fail validation."""
        with pytest.raises(Exception):
            RejectedCandidate(
                candidate_text="test",
                reason="INVALID_REASON",
            )

    def test_extraction_result_with_rejections(self):
        """ExtractionResult should accept RejectedCandidate entries."""
        result = ExtractionResult(
            source_file="test.txt",
            source_section="Test §1",
            candidates_found=2,
            parameters_extracted=0,
            parameters=[],
            rejected_candidates=[
                RejectedCandidate(
                    candidate_text="test candidate",
                    reason=RejectionReason.NOT_ISA_VISIBLE,
                    detail="Not observable via ISA",
                )
            ],
        )
        assert len(result.rejected_candidates) == 1
        assert result.rejected_candidates[0].reason == RejectionReason.NOT_ISA_VISIBLE


# ──────────────────────────────────────────────────────────────────────
# R6: Evidence Heuristic Checks
# ──────────────────────────────────────────────────────────────────────

class TestEvidenceHeuristics:
    """Test the secondary evidence quality heuristics."""

    def test_ellipsis_detected(self):
        """Evidence with '...' should be flagged."""
        warnings = validate_evidence_heuristics(
            "the size of a cache block ... are implementation-specific",
            "the size of a cache block and the organization are implementation-specific",
        )
        assert any("ELLIPSIS" in w for w in warnings)

    def test_unicode_ellipsis_detected(self):
        """Evidence with unicode ellipsis '…' should be flagged."""
        warnings = validate_evidence_heuristics(
            "the size\u2026 are implementation-specific",
            "the size and organization are implementation-specific",
        )
        assert any("ELLIPSIS" in w for w in warnings)

    def test_mid_clause_after_conjunction_detected(self):
        """Evidence starting mid-clause after 'and' should be flagged."""
        source = "The capacity and organization of a cache and the size of a cache block are both implementation-specific"
        evidence = "the size of a cache block are both implementation-specific"
        warnings = validate_evidence_heuristics(evidence, source)
        assert any("MID_CLAUSE" in w for w in warnings)

    def test_clean_evidence_passes(self):
        """Clean, well-formed evidence should produce no warnings."""
        source = "The mechanism to perform such an operation is implementation-specific."
        evidence = "The mechanism to perform such an operation is implementation-specific."
        warnings = validate_evidence_heuristics(evidence, source)
        assert len(warnings) == 0

    def test_sentence_start_evidence_passes(self):
        """Evidence starting at the beginning of a sentence should pass."""
        source = "Implementations might allow a more-privileged level to trap."
        evidence = "Implementations might allow a more-privileged level to trap."
        warnings = validate_evidence_heuristics(evidence, source)
        assert len(warnings) == 0
