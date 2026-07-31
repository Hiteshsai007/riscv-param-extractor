# Claim Ledger (R11)

Every bolded metric in `README.md` mapped to the exact file/script that produced it. The purpose is to turn "trust me" into "check this line."

## Checkable Claims

| Claim | Reported Value | Source File | Verification Command |
|-------|---------------|-------------|---------------------|
| **Precision (Strict)** — historical Run 5 | 0.3846 | `results/run_20260717_053803/*.yaml` vs gold with `data/gold/archive/pre_r1_fix/cache_block_size.yaml` overlay | `python scripts/verify.py` |
| **Recall (Strict)** — historical Run 5 | 0.5000 | Same (pre-R1 archived gold) | `python scripts/verify.py` |
| **F1 (Strict)** — historical Run 5 | 0.4348 | Same (pre-R1 archived gold) | `python scripts/verify.py` |
| **Precision (Relaxed)** — historical | 0.5000 | Same source, `src/eval_harness.py:compute_precision_recall_relaxed` | `python scripts/verify.py` (partial) |
| **Recall (Relaxed)** — historical | 0.6000 | Same source | `python scripts/verify.py` (partial) |
| **F1 (Relaxed)** — historical | 0.5455 | Same source | `python scripts/verify.py` (partial) |
| **Hallucination Rate** — historical | 0.0% | `src/validate_yaml.py:validate_evidence_grounding` | `python scripts/verify.py` |
| **Gold R1 correction (P0.1)** | `cache_capacity_and_organization` → `rejected_candidates` / `NOT_ISA_VISIBLE` | Live: `data/gold/positive_cases/cache_block_size.yaml`; archive: `data/gold/archive/pre_r1_fix/` | `python scripts/verify.py` (prints F1 delta on Run 5 artifacts) |
| **Precision / Recall / F1** — live full corpus (30) | 0.5000 / 0.1154 / 0.1875 | `results/run_20260730_152612/` vs current `data/gold/` | `python scripts/verify.py` |
| **Hallucination Rate** — live | 0.0% | Same live run | `python scripts/verify.py` |
| **Set A only (live, from full run)** | P 1.0000 / R 0.3333 / F1 0.5000 | Same live run, Set A slice | `python scripts/compute_eval_breakdown.py --results results/run_20260730_152612` |
| **Sets B–D (first forward-registered eval)** | P 0.0000 / R 0.0000 / F1 0.0000 | Same live run, B–D slice | `python scripts/compute_eval_breakdown.py --results results/run_20260730_152612` |
| **Full 30 F1 (post-fix §8)** | 0.2353 | `results/run_qwen_fast/` vs current `data/gold/` | `python scripts/compute_eval_breakdown.py --results results/run_qwen_fast` |
| **Set A F1 (post-fix §8)** | 0.5333 | Same post-fix run, Set A slice | Same |
| **Grounding recall (Set A, v6)** | 0.4444 (full Set A) / 0.6000 (name-leaked subset) | `results/run_20260730_160338/` + prompt `v6_decision_framework` | `python scripts/compute_eval_breakdown.py --results results/run_20260730_160338 --discovery-results results/run_20260730_162340` |
| **Discovery recall (Set A, v8)** | 0.0000 | `results/run_20260730_162340/` + prompt `v8_discovery` (`config/discovery.yaml`) | same |
| **Run-to-run variance ΔF1 (Set A)** | 0.0000 | `results/run_20260730_160338` vs `results/run_20260730_161322` | compare summaries / breakdown |
| **YAML Validity** | 100% | `src/validate_yaml.py:validate_parameter_schema` | `python scripts/verify.py` |
| **Ground truth precommitted** | Yes | `data/ground_truth/*.yaml` | `python scripts/check_commit_order.py` |
| **Unit test suite** | 48/48 pass | `tests/` incl. `tests/test_isa_verification.py` | `python -m pytest tests/ -v` |
| **ISA-claims verifier** | git-tracked results only (default) | `scripts/verify_isa_claims.py` | `python scripts/verify_isa_claims.py` |
| **Prompt leakage guard** | v8 clean; v4–v7 allowlisted grounding | `scripts/check_prompt_leakage.py` | `python scripts/check_prompt_leakage.py` |
| **Corpus 1:1:1 integrity** | 30 snippets ↔ 30 GT ↔ 30 gold (24 pos/6 neg) | `data/raw_snippets/` ↔ `data/ground_truth/` ↔ `data/gold/{positive,negative}_cases/` | count files |
| **Commit-order integrity (R4)** | GT predates results for all snippets | `scripts/check_commit_order.py` | `python scripts/check_commit_order.py` |
| **UDB-shaped export (P3.1)** | format samples under `results/udb/`; **no upstream PR** | live `wlrl_*` / `satp_asid_bits` + reference `CACHE_BLOCK_SIZE` shape | inspect `results/udb/README.md` |

## Claims NOT Being Made

1. **Historical Run 5 recall is NOT discovery recall.** The v6 prompt embeds gold names for several Set A snippets. Live P1.1 separates columns: grounding (v6) vs discovery (v8).

2. **This is NOT a multi-model finding of success.** No second model has committed post-gate artifacts under the unified gate.

3. **This is NOT an upstream contribution to UDB.** `results/udb/` holds format samples. Live `cache_block_size` extracted zero accepted parameters; decision: **do not open an upstream PR**.

4. **The ISA-visibility gate IS live-validated with committed artifacts (resolved Hardening Pass 2).** Primary tree: `results/run_20260730_152612/` (YAMLs contain `isa_visible`). Arena/sandbox Ollama remains environment-blocked; this machine ran local Ollama successfully.

5. **Relaxed matching inflates precision/recall** on historical numbers (R9).

6. **Set-A gold R1 contradiction is FIXED (P0.1).** See archive + live gold.

7. **The expanded 30-snippet corpus HAS been evaluated (P1.3).** Full-corpus live F1 = 0.1875. The ±0.15 falsification condition vs historical 0.4348 **triggered** — Set-A-only historical F1 does not generalize to the forward-registered Sets B–D (first-eval F1 = 0.0000). That failure is intentional measurement integrity, not a silent gap: see [`docs/ERROR_ANALYSIS.md`](docs/ERROR_ANALYSIS.md).

8. **Discovery prompt exact-match recall is NOT “the model found nothing.”** On WLRL/CSR-trap it emitted illustrative `v8_discovery` example names (`legal_encoding_subset`, `privileged_csr_intercept`) instead of gold names — a naming contamination failure mode, not empty extraction.

9. **Multi-model success is NOT claimed.** Only Qwen post-gate artifacts are committed under the unified ISA gate. Earlier incomplete Llama attempts are not advertised as cross-model success.

10. **No upstream UDB PR yet.** [`results/udb/`](results/udb/) holds format samples. Post-fix §8, `cache_block_size` is now accepted with CBO.ZERO/CBO.CLEAN citation — a UDB PR is now viable pending full-corpus quality review.

## Metric Computation Chain

```
Raw snippets (data/raw_snippets/*.txt)
    → Pipeline extraction (src/extract.py + LLM + live ISA gate)
        → Result YAMLs (results/run_20260717_053803/*.yaml)          [historical]
        → Result YAMLs (results/run_20260730_152612/)                [live full corpus]
        → Result YAMLs (results/run_20260730_160338|161322/)         [Set A variance]
        → Result YAMLs (results/run_20260730_162340/)                [discovery prompt]
            → Evaluation harness (src/eval_harness.py)
                → historical: gold with archive/pre_r1_fix overlay
                → live:       current data/gold/ (R1-corrected)
                    → precision, recall, F1, hallucination rate
                        → reported in README.md + CLAIM-LEDGER.md
                            → verified by scripts/verify.py / ./verify.sh
```

Every link in this chain is committed to the repository and can be inspected without running a model.
