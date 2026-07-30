# Claim Ledger (R11)

Every bolded metric in `README.md` mapped to the exact file/script that produced it. The purpose is to turn "trust me" into "check this line."

## Checkable Claims

| Claim | Reported Value | Source File | Verification Command |
|-------|---------------|-------------|---------------------|
| **Precision (Strict)** | 0.3846 | `results/run_20260717_053803/*.yaml` vs `data/gold/` | `python scripts/verify.py` |
| **Recall (Strict)** | 0.5000 | `results/run_20260717_053803/*.yaml` vs `data/gold/` | `python scripts/verify.py` |
| **F1 (Strict)** | 0.4348 | `results/run_20260717_053803/*.yaml` vs `data/gold/` | `python scripts/verify.py` |
| **Precision (Relaxed)** | 0.5000 | Same source, `src/eval_harness.py:compute_precision_recall_relaxed` | `python scripts/verify.py` (partial) |
| **Recall (Relaxed)** | 0.6000 | Same source | `python scripts/verify.py` (partial) |
| **F1 (Relaxed)** | 0.5455 | Same source | `python scripts/verify.py` (partial) |
| **Hallucination Rate** | 0.0% | `src/validate_yaml.py:validate_evidence_grounding` | `python scripts/verify.py` |
| **YAML Validity** | 100% | `src/validate_yaml.py:validate_parameter_schema` | `python scripts/verify.py` |
| **Ground truth precommitted** | Yes | `data/ground_truth/*.yaml` | `python scripts/check_commit_order.py` |
| **Unit test suite** | 46/46 pass (re-run 2026-07-30) | `tests/` incl. `tests/test_isa_verification.py` (5 gate/verifier tests) | `python3 -m pytest tests/ -v` |
| **ISA-claims verifier on committed runs** | Checked 0, exit 0 (2026-07-30) | `scripts/verify_isa_claims.py` over `results/run_20260717_*`; those files predate the visibility fields (grep: 0 files contain `isa_visible`) so 0 checked is expected, not a path bug | `python3 scripts/verify_isa_claims.py` |
| **Reproducibility re-derivation** | 4/4 metrics match (2026-07-30) | `scripts/verify.py` re-computes P/R/F1/hallucination from committed YAMLs | `python3 scripts/verify.py` |

## Claims NOT Being Made

These are things this repository explicitly **does not** claim, to avoid ambiguity:

1. **This is NOT discovery recall.** The v6 prompt includes gold parameter names for 2 of 10 snippets. The reported recall conflates grounding recall (matching known catalogue) with cold discovery recall (finding novel parameters). See README → "Recall Type Disclosure (R8)."

2. **This is NOT a multi-model finding of success.** The cross-model evaluation between Qwen 2.5 7B and Llama 3.1 8B initially revealed a prompt instruction breakdown. The parser leak, silent field-absence rejection, and later hallucinated self-certification are now resolved (2026-07-30), but a fresh multi-model run is still required before claiming cross-model success. See README -> "Confound Reporting".

3. **This is NOT an upstream contribution to UDB.** The `generate_spec_tags.py` script produces UDB-format YAML, but no PR has been opened because the pipeline failed to produce novel, well-formatted discoveries in the final run. Cross-referencing UDB is for validation, not a contribution claim.

4. **The ISA-visibility gate and verifier are unified (resolved 2026-07-30), but NOT live-validated with committed artifacts.** `extract.py` synchronously requires `isa_visible: true`, a substantive justification, and a real instruction/CSR mnemonic via the shared `src/isa_verification.py` function. The verifier imports that same function. The three discovered failure modes—parser leak, silent field-absence rejection, and hallucinated self-certification—are closed at unit level (46/46 pytest, re-run 2026-07-30); the historical origin and dates are recorded in README → "Confound Reporting". As of 2026-07-30, no post-unification live-model run has committed artifacts in this repository: `run_20260730_113320` is cited in commit `4b1a063`'s message but never appears in git history (`git rev-list --all --objects | grep run_20260730` → empty), and a live re-test attempt on 2026-07-30 was environment-blocked (no Ollama binary, model registries unreachable, 3.8 GB RAM < ~4.4 GB weights). The unification commit `a75f5b7` IS an ancestor of `origin/main` (merged via PR #1); the old `arena/019fb244-*` branch was deleted after merge, and `main` is the authoritative branch going forward.

5. **Relaxed matching inflates precision/recall.** The relaxed metric uses `SequenceMatcher ≥ 0.75`, which can credit near-misses. The exact-match and relaxed-match numbers are reported side by side (R9) so the reader can judge the gap.

## Metric Computation Chain

```
Raw snippets (data/raw_snippets/*.txt)
    → Pipeline extraction (src/extract.py + LLM)
        → Result YAMLs (results/run_20260717_053803/*.yaml)
            → Evaluation harness (src/eval_harness.py)
                → compare against gold labels (data/gold/)
                    → precision, recall, F1, hallucination rate
                        → reported in README.md
                            → verified by scripts/verify.py
```

Every link in this chain is committed to the repository and can be inspected without running a model.
