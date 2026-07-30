# Ground Truth Ledger (R4)

This file indexes the precommitted ground truth annotations for the LFX evaluation corpus.

**Corpus status (2026-07-30):** 30 snippets, 30 ground-truth files, 30 gold labels —
a strict 1:1:1 mapping (`data/raw_snippets/*.txt` ↔ `data/ground_truth/*.yaml` ↔ `data/gold/{positive,negative}_cases/*.yaml`).
`check_commit_order.py` verifies every ground-truth file was committed before any result for the same snippet.

**Which file grades what:**
- `data/gold/{positive,negative}_cases/*.yaml` — the **grading truth** consumed by `src/eval_harness.py` (matching is on `name` + `type` only).
- `data/ground_truth/*.yaml` — the **R4 preregistration record** (existence + commit order enforced by `scripts/check_commit_order.py`). Preregistered names/types were copied verbatim into the gold labels on 2026-07-30, before any pipeline run on those snippets.

## Set A — Evaluated set (10 snippets, gold labels predate all runs)

Grading truth committed alongside the original runs; published metrics (P 0.3846 / R 0.5000 / F1 0.4348 strict) are computed over exactly this set.

1. **cache_block_size** (positive)
2. **cbo_zero_atomicity** (positive)
3. **cmo_trigger_behavior** (positive — R4 preregistration expected 1 param; gold labels 2: `cmo_trigger_module_behavior`, `cmo_trigger_match_type`. Gold is authoritative; drift recorded in the GT file header.)
4. **csr_address_encoding** (negative)
5. **csr_trap_intercept** (positive)
6. **debug_csr_access** (negative)
7. **non_coherent_agent_mechanism** (positive)
8. **warl_field_behavior** (positive)
9. **wlrl_field_behavior** (positive)
10. **wpri_field_behavior** (negative)

## Set B — Forward-registered set (15 snippets; GT committed 2026-07-29 in `f1f3b52`, gold labels authored 2026-07-30 before any run)

11. **pmp_granularity** (positive)
12. **asid_width** (positive)
13. **vlen_size** (positive)
14. **elen_size** (positive)
15. **pte_a_d_update_mechanism** (positive)
16. **stval_illegal_inst_behavior** (positive)
17. **nmi_cause_update** (positive)
18. **misa_writability** (positive)
19. **mvendorid_value** (positive)
20. **marchid_value** (positive)
21. **mimpid_value** (positive)
22. **mconfigptr_presence** (positive)
23. **hpmcounter_width** (positive)
24. **mmu_tlb_size** (negative)
25. **branch_predictor_type** (negative)

## Set C — Registered but previously unindexed (3 snippets; GT committed 2026-07-29 in `f1f3b52`, index entry added 2026-07-30)

These GT files existed since 2026-07-29 but were missing from this ledger — a documentation gap, not a missing preregistration. `stack_pointer_reset` and `perf_counters`/`smstval_extension` also used non-canonical GT formats, normalized 2026-07-30.

26. **perf_counters** (positive)
27. **smstval_extension** (positive)
28. **stack_pointer_reset** (negative)

## Set D — Added 2026-07-30 (2 snippets, reaching the ≥30 falsification corpus size)

Authored and committed together with their gold labels, **before any pipeline run**, so the expanded evaluation (P1.2) remains falsification-safe.

29. **mtvec_base_alignment** (positive)
30. **pmp_region_count** (positive)

## 2026-07-30 registry integrity fix (justifications + index vocabulary)

An offline audit on 2026-07-30 (`justification_cites_real_mnemonic` over all GT files) found that
**12 of 18 forward-registered `isa_visible: true` justifications were unpassable by construction**:
they cited real RISC-V names (VSETVLI, MARCHID, MIMPID, MVENDORID, MHPMCOUNTER3, PMPCFG/PMPADDR) that were
simply **absent from the checked-in index** (`data/riscv_isa_index.json` had 44 instructions / 40 CSRs —
no vector instructions, no ID CSRs, no PMP CSRs, no performance-counter CSRs). A live gate over this corpus
would have silently rejected those parameters no matter how good the model was — a reference-vocabulary
false-rejection bug, masquerading as a model failure.

Fix (same commit, pre-registration, before any live run on these snippets):
- `data/riscv_isa_index.json` expanded to 48 instructions / 267 CSRs — only real RISC-V mnemonics added
  (vector config, ID/counter/PMP/debug/trigger/RNMI CSRs). No generic categories (CMO stays excluded).
- The 12 affected GT justifications rewritten to cite indexed mnemonics (names/types unchanged).
- `data/ground_truth/{warl,wlrl,cmo_trigger_behavior,csr_trap_intercept,non_coherent_agent_mechanism}.yaml`
  similarly updated (their `isa_visible: true` entries also failed the check; grading is via `data/gold`,
  so published metrics are unaffected).

See README → Confound Reporting for the full audit trail.
