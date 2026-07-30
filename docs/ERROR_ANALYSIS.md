# Error Analysis — Live Unified Gate & Discovery

Concrete misses from committed artifacts. Low B–D / discovery scores are
**measurement honesty**, not hidden bugs we refuse to name.

Primary live run: [`results/run_20260730_152612/`](../results/run_20260730_152612/)  
Discovery run: [`results/run_20260730_162340/`](../results/run_20260730_162340/)  
Gold: [`data/gold/`](../data/gold/)

## Live full corpus (`run_20260730_152612`, prompt `v6`)

| Snippet | Gold | Model did | Failure mode |
|---------|------|-----------|--------------|
| `cache_block_size` | `cache_block_size` | empty; 2× `NOT_ISA_VISIBLE` rejections | Gate + model collapsed capacity *and* block-size into one rejected candidate; true positive not recovered |
| `cbo_zero_atomicity` | `cbo_zero_atomicity_and_granularity` | empty; 1 rejection | Over-rejection / missed ISA justification for a real CBO parameter |
| `cmo_trigger_behavior` | `cmo_trigger_module_behavior`, `cmo_trigger_match_type` | empty; 1 rejection | Multi-param miss under strict visibility |
| `non_coherent_agent_mechanism` | `non_coherent_agent_cbo_mechanism` | empty (0 params, 0 rejections) | Candidate reached Pass 2 but nothing accepted — silent under-extraction |
| `warl_field_behavior` | `warl_supported_values` | empty | Same class: WARL variability present in gold, absent in live output |
| `asid_width` | `asid_width` | `satp_asid_bits` | **Near miss** — correct concept, wrong canonical name (exact-match FN) |
| `vlen_size` | `vlen_size` | `vlen_value` | Near miss (naming), not empty |
| `misa_writability` | `misa_writability` | `misa_writable` | Near miss (naming) |
| Most Sets B–D positives (`pmp_*`, `hpmcounter_width`, `pte_a_d_*`, …) | 1 expected each | empty | First forward-registered eval: **aggregate B–D F1 = 0.0000** |

Accepted under the same gate (for contrast): `wlrl_supported_values`, `wlrl_illegal_write_exception`, `csr_access_trap_capability`, plus the near-misses above.

## Discovery Set A (`run_20260730_162340`, prompt `v8_discovery`)

Zero evaluation gold names in the prompt. Exact-match Set A recall = **0.0000**.

| Snippet | Gold | Model did | Failure mode |
|---------|------|-----------|--------------|
| `wlrl_field_behavior` | `wlrl_supported_values`, `wlrl_illegal_write_exception` | `legal_encoding_subset`, `illegal_encoding_trap` | **Naming contamination** — reused illustrative off-evaluation example names from `v8_discovery` |
| `csr_trap_intercept` | `csr_access_trap_capability` | `privileged_csr_intercept` | Same: illustrative example name, not gold catalogue name |
| `cache_block_size` / `cmo_trigger_*` / `warl_*` | gold params | empty | Cold discovery did not surface catalogue names |

This is why historical / v6 recall must **not** be labeled “discovery recall.”

## How to re-check

```bash
python scripts/compute_eval_breakdown.py --results results/run_20260730_152612
python scripts/compute_eval_breakdown.py \
  --results results/run_20260730_160338 \
  --discovery-results results/run_20260730_162340
./verify.sh
```

## What we are not claiming

- That a larger model would fix B–D (untested; no second-model post-gate artifacts committed).
- That leaking gold names into `v8_discovery` is an acceptable way to raise discovery recall.
- That empty extraction always means “gate too strict” — several cases are naming near-misses or prompt-example contamination.
