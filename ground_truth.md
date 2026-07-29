# Ground Truth Ledger (R4)

This file indexes the precommitted ground truth annotations for the LFX evaluation corpus.
The actual machine-readable ground truth data is located in `data/ground_truth/*.yaml`.

By committing this ledger and the corresponding YAML files *before* any pipeline result is committed, we prove that the pipeline predictions are being evaluated against a pre-registered rubric, rather than the rubric being retroactively adjusted to fit the model's outputs.

You can verify the commit ordering mathematically using:
```bash
python scripts/check_commit_order.py
```

## Annotated Snippets

1. **cache_block_size**
   - Expected Parameters: `cache_block_size` (numeric_range)
   - Expected Rejections: `The capacity and organization of a cache` (Reason: `NOT_ISA_VISIBLE`)
2. **cbo_zero_atomicity**
3. **cmo_trigger_behavior**
4. **csr_address_encoding**
5. **csr_trap_intercept**
6. **debug_csr_access**
7. **non_coherent_agent_mechanism**
8. **warl_field_behavior**
9. **wlrl_field_behavior**
10. **wpri_field_behavior**

*(See `data/ground_truth/*.yaml` for full reason-codes, rationales, and visibility justifications)*
