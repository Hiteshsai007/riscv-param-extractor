# Coding Challenge Exam (2 Snippets)

This directory contains the strict 2-snippet exam designed to test the parameter extraction pipeline against the exact LFX coding challenge requirements.

## The Exam

The exam consists of two short ISA passages (~185 words total):

1. **CMO / Cache Block** (`cmo_cache_block.txt`)
   - **Expected Yield**: `cache_block_size` (ISA-visible; visible to `CBO.*` instructions).
   - **Expected Rejection**: Cache capacity/organization (rejected as `NOT_ISA_VISIBLE`).
   - **Expected Rejection**: "Shall be uniform" (rejected as a constraint, not a parameter).

2. **CSR Address Mapping** (`csr_address_mapping.txt`)
   - **Expected Yield**: **Zero** parameters.
   - **Expected Rejection**: CSR encoding spaces, read/write accessibility, privilege levels (rejected as fixed ISA rules, not implementation-defined parameters).

## Strict Pure-Prompt Honesty

To prevent the LLM from simply memorizing the answer, the exam uses a **pure prompt** (`prompts/exam_v2.md`). 
- **Zero** evaluation-snippet answer strings are leaked in the prompt.
- **No** mention of "cache_block_size" or "CBO.ZERO" in the few-shot examples.
- Guarded by `scripts/check_prompt_leakage.py`.

## Exam Results (run_20260731_180301)

| Snippet | Candidate | Model Output | Gate | Lesson |
|---------|-----------|--------------|------|--------|
| CMO / Cache Block | `cache_block_size` | ❌ Extracted generic `CMO` | ❌ Rejected (`justification_cites_real_mnemonic`) | A 7B model lacks the explicit zero-shot knowledge to bridge "CMO extensions" in text to the concrete `CBO.ZERO` mnemonic without few-shot examples. The strict gate correctly rejected it for lacking a specific mnemonic citation. |
| CMO / Cache Block | Cache capacity / organization | ❌ Extracted generic `CMO` | ❌ Rejected (`justification_cites_real_mnemonic`) | Also failed the mnemonic citation check. |
| CSR Address Mapping | (None found) | ✅ 0 parameters | — | The pipeline correctly avoids hallucinating false-positive parameters from standard ISA rules. |

## Predictions Confirmed / Refuted

Prior to the run, we documented falsifiable predictions in [`predictions.md`](predictions.md).
1. **Confirmed:** Models over-extract cache capacity but the gate rejects it (via the mnemonic check).
2. **Confirmed:** The CSR snippet yields zero accepted parameters.
3. **Confirmed:** A generic "CMO" justification that fails to cite a specific instruction mnemonic fails the ISA-visibility gate.
4. **Refuted:** We predicted the model would successfully cite `CBO.*` independently. It failed to do so, instead citing the generic "CMO instructions". The pure prompt demonstrates that the model cannot jump from "CMO" to "CBO.ZERO" without an explicit example, validating the necessity of the strict gate.

## Run It Yourself

```bash
python -m src.cli --input challenge/snippets --config challenge/exam_config.yaml
```
