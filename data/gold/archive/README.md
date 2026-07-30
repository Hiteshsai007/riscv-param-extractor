# Gold Label Archive

Historical gold labels retained so published metrics remain independently re-derivable
after doctrine corrections to the live grading set under `data/gold/{positive,negative}_cases/`.

## `pre_r1_fix/`

Snapshot of `cache_block_size.yaml` **before** the R1 / NOT_ISA_VISIBLE correction
(Hardening Pass 2, P0.1, 2026-07-30).

- **Why archived:** The live gold incorrectly listed `cache_capacity_and_organization`
  as an expected parameter. That contradicts ISA-visibility doctrine (R1) and the
  corrected README example. The parameter belongs in `rejected_candidates` with
  reason `NOT_ISA_VISIBLE`.
- **What used it:** Run 5 metrics (`results/run_20260717_053803`) were graded against
  this pre-correction label. Strict P/R/F1 = 0.3846 / 0.5000 / 0.4348.
- **How to re-derive historical numbers:**
  `python scripts/verify.py` overlays this archived file onto the current gold set
  when scoring the historical run, then scores the live unified-gate run against
  current gold.

Do not silently edit files in this archive. New gold revisions go under
`data/gold/positive_cases/` or `data/gold/negative_cases/`.
