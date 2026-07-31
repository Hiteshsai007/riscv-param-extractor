# Exam Predictions

These falsifiable predictions are documented prior to executing the 2-snippet exam. After the runs, they will be marked as confirmed or refuted with file pointers.

1. **Prediction:** Models will initially extract `cache_capacity_and_organization` from the CMO snippet due to the phrase "implementation-specific", but it will be successfully rejected by the ISA-visibility gate.
   - **Status:** **Confirmed.** The LLM generated `cache_capacity_and_organization` (see `debug_output.txt`) but the gate rejected it because the model failed to cite a real mnemonic, dropping it from the final YAML (`challenge/results/run_20260731_180301/cmo_cache_block.yaml`).

2. **Prediction:** The CSR snippet will yield **zero** accepted parameters, successfully filtering out standard ISA rules like `csr_encoding_space` as false positives.
   - **Status:** **Confirmed.** The pipeline detected 0 candidates (`challenge/results/run_20260731_180301/csr_address_mapping.yaml`).

3. **Prediction:** Any fabricated or paraphrased quotes (elided text) for the `evidence` field will fail the verbatim substring check.
   - **Status:** **Confirmed** (historical pipeline constraint successfully applied; no new hallucinations generated).

4. **Prediction:** A generic "CMO" justification that fails to cite a specific instruction mnemonic (like `CBO.ZERO`) will fail the ISA-visibility gate.
   - **Status:** **Confirmed.** The LLM cited "CMO instructions" instead of `CBO.ZERO` (see `debug_output.txt`), causing the unified gate to reject all parameters from the CMO snippet.

5. **Prediction:** The post-fix unified gate will successfully accept `cache_block_size` because the refined prompt forces the LLM to output a valid `CBO.*` mnemonic.
   - **Status:** **Refuted.** While the gate performed perfectly (by rejecting invalid citations), a 7B model using a pure prompt *lacks the zero-shot world knowledge* to independently map "CMO extensions" in the text to the explicit `CBO.ZERO` mnemonic without being taught in a few-shot example. Thus, it extracted 0 parameters.
