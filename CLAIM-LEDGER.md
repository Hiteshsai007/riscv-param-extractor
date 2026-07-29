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

## Claims NOT Being Made

These are things this repository explicitly **does not** claim, to avoid ambiguity:

1. **This is NOT discovery recall.** The v6 prompt includes gold parameter names for 2 of 10 snippets. The reported recall conflates grounding recall (matching known catalogue) with cold discovery recall (finding novel parameters). See README → "Recall Type Disclosure (R8)."

2. **This is NOT a multi-model finding of success.** The cross-model evaluation between Qwen 2.5 7B and Llama 3.1 8B initially revealed a prompt instruction breakdown. After fixing the formatting and the overly strict ISA-visibility gate (which silently rejected all candidates due to a missing field), we now have a working pipeline. See README -> "Confound Reporting".

3. **This is NOT an upstream contribution to UDB.** The `generate_spec_tags.py` script produces UDB-format YAML, but no PR has been opened because the pipeline failed to produce novel, well-formatted discoveries in the final run. Cross-referencing UDB is for validation, not a contribution claim.

4. **The ISA-visibility gate is enforced mechanically.** Unlike previous versions that trusted the LLM, the pipeline script itself (`extract.py`) actively enforces the 3-part ISA-visibility test and rejects candidates that the LLM incorrectly formats or fails to justify.

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
