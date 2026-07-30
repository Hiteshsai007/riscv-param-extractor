"""Shared verification for ISA-visibility justifications.

The extraction gate and the post-run audit must use exactly the same definition
of a verifiable ISA claim: the justification names a real instruction or CSR
from the repository's ISA index.
"""

import json
import re
from pathlib import Path


_WORD_PATTERN = re.compile(r"\b[A-Z0-9_.]+\b")
_INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "riscv_isa_index.json"


def _load_isa_index() -> tuple[set[str], set[str]]:
    """Load the checked-in instruction and CSR vocabulary."""
    with _INDEX_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return set(data.get("valid_instructions", [])), set(data.get("valid_csrs", []))


def justification_cites_real_mnemonic(justification: str) -> bool:
    """Return whether *justification* cites an indexed instruction or CSR.

    Matching deliberately mirrors the former verifier: uppercase RISC-V names
    (including dotted instruction names) are extracted and checked against the
    checked-in index.  Keeping the index lookup here makes the live gate and
    the audit script impossible to accidentally desynchronise.
    """
    if not isinstance(justification, str):
        return False
    valid_instructions, valid_csrs = _load_isa_index()
    return any(
        word in valid_instructions or word in valid_csrs
        for word in _WORD_PATTERN.findall(justification)
    )
