"""Regression tests for ISA-visibility mnemonic verification.

Ensures that generic extension or category names (such as CMO) are rejected
as standalone ISA mnemonics, while genuine instruction and CSR mnemonics
are accepted.
"""

from src.isa_verification import _load_isa_index, justification_cites_real_mnemonic


class TestISAVerification:
    """Test suite for ISA mnemonic matching in visibility justifications."""

    def test_load_isa_index_excludes_generic_cmo_category(self):
        """Generic category name CMO must not be included in valid instructions."""
        valid_instructions, valid_csrs = _load_isa_index()
        assert "CMO" not in valid_instructions
        assert "CBO.ZERO" in valid_instructions
        assert "CBO.CLEAN" in valid_instructions
        assert "MSTATUS" in valid_csrs

    def test_rejects_generic_cmo_category_justification(self):
        """A justification citing only 'CMO' without a specific instruction is rejected."""
        assert justification_cites_real_mnemonic("CMO instructions operate on cache-block-sized granules.") is False
        assert justification_cites_real_mnemonic("This parameter affects CMO behavior.") is False
        assert justification_cites_real_mnemonic("CMO") is False

    def test_accepts_real_cbo_instruction_mnemonic(self):
        """A justification citing specific CBO instructions is accepted."""
        assert (
            justification_cites_real_mnemonic(
                "CBO.ZERO and CBO.CLEAN operate on cache-block-sized granules."
            )
            is True
        )
        assert (
            justification_cites_real_mnemonic(
                "CMO instructions such as CBO.ZERO operate on cache granules."
            )
            is True
        )
        assert justification_cites_real_mnemonic("CBO.INVAL instruction behavior") is True

    def test_accepts_real_csr_mnemonic(self):
        """A justification citing a valid CSR is accepted."""
        assert (
            justification_cites_real_mnemonic(
                "Software can observe this trap when reading MSTATUS."
            )
            is True
        )
        assert (
            justification_cites_real_mnemonic(
                "Software can read back the CSR with CSRRS to check values."
            )
            is True
        )

    def test_rejects_empty_or_non_string_justifications(self):
        """Non-string or empty justifications must return False."""
        assert justification_cites_real_mnemonic("") is False
        assert justification_cites_real_mnemonic("no uppercase instruction names here") is False
        assert justification_cites_real_mnemonic(None) is False
        assert justification_cites_real_mnemonic(123) is False
