# Ground Truth: 2-Snippet Exam

This file predates the challenge evaluations and serves as the strict grading standard.

## 1. cmo_cache_block.txt
Source: `data/raw_snippets/cache_block_size.txt` (~Priv §19.3.1)

### Accepted
- **`cache_block_size`**
  - Justification: ISA-visible. Determines the granularity of CBO.* instructions (e.g., CBO.ZERO, CBO.CLEAN, CBO.FLUSH).
  - Must cite a valid instruction mnemonic to pass the ISA-visibility gate.

### Rejected
- **`cache_capacity_and_organization`** (or `cache_capacity`, `cache_organization`)
  - Reason Code: `NOT_ISA_VISIBLE`
  - Explanation: Cache capacity and internal organization do not alter the architectural behavior of instructions.
- **`shall_be_uniform`** (or `uniform_cache_block_size`)
  - Reason Code: `CONSTRAINT_NOT_PARAMETER`
  - Explanation: "shall be uniform" is a rule/constraint applied to the cache block size, not an independent parameter.

---

## 2. csr_address_mapping.txt
Source: `data/raw_snippets/csr_address_encoding.txt` (~Priv §2.1)

### Accepted
- **None** (0 challenge-type parameters expected).

### Rejected (Likely False Positives)
- **`csr_encoding_space`** (or `csr_address_space`)
  - Reason Code: `NOT_IMPLEMENTATION_DEFINED` (or `ISA_FIXED_RULE`)
  - Explanation: The 12-bit encoding space is a fixed ISA standard, not an implementation-defined choice.
- **`csr_read_write_accessibility`**
  - Reason Code: `NOT_IMPLEMENTATION_DEFINED`
  - Explanation: Fixed by ISA convention (upper 4 bits).
- **`csr_privilege_level`**
  - Reason Code: `NOT_IMPLEMENTATION_DEFINED`
  - Explanation: Fixed by ISA convention (bits [9:8]).
