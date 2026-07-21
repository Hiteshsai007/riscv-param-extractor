# Experiment Log: Prompt Engineering Iterations

This document serves as the official engineering experiment log for the prompt iterations of the RISC-V Architectural Parameter Extractor. It captures the goal, changes, observed metrics, failure analysis, and lessons learned for each prompt iteration.

## Run 1 — v1_baseline
**Date:** 2026-07-16
**Model:** Qwen 2.5 7B Instruct (Ollama)
**Prompt version:** v1_baseline
**Goal:** Establish a zero-shot baseline measuring how well instruction-following alone handles the 3-way classification problem and schema compliance.
**Config:** temperature=0.0, seed=42

**Results:**
| Metric | Value |
|--------|-------|
| Precision | 0.0 |
| Recall | 0.0 |
| F1 | 0.0 |
| Hallucination rate | 0.0 |
| YAML validity rate | 0.0 (0/10) |

**Failure analysis:**
The 7B model entirely failed to comprehend the Pydantic schema structure dumped directly into the prompt without a concrete example. It emitted single dicts with missing fields or a list of raw strings instead of emitting a YAML array of objects. The extraction loop correctly caught these as Pydantic Validation Errors, resulting in 0 extractions.

**Lessons learned:** Instruction-tuned 7B models strictly need a clear 1-shot formatting example to reliably conform to a rigid, multi-field YAML schema.

**Next iteration (v2):** Add a strict, 1-shot formatting example of the exact YAML output structure.

---

## Run 2 — v2_few_shot
**Date:** 2026-07-16
**Model:** Qwen 2.5 7B Instruct (Ollama)
**Prompt version:** v2_few_shot
**Goal:** Fix output formatting through few-shot demonstration.

**Results:**
| Metric | Value |
|--------|-------|
| Precision | 0.1667 (1/6) |
| Recall | 0.10 (1/10) |
| F1 | 0.125 |
| Hallucination rate | 0.0 |
| YAML validity rate | 1.0 (6/6) |

**Failure analysis:**
The 1-shot example worked perfectly to fix the YAML structure (Validity Rate 0% -> 100%). Hallucination rate remained 0%. However, classification logic proved extremely weak.
- **False Positives (5):** Extracted `cache_capacity` instead of combining it into structural organization. Extracted boolean fields that are structural conventions.
- **False Negatives (9):** Completely missed complex parameter fields like WLRL/WARL behavior. The model forces early categorization without deeply understanding the difference between a mandatory struct and a legitimate variability axis.

**Lessons learned:** The model needs explicit reasoning capabilities and contrastive examples to distinguish between software permissions, mandatory behavior, and genuine hardware variability.

**Next iteration (v3/v4):** Introduce Chain-of-Thought (CoT) and contrastive few-shot examples (positive vs negative). 

---

## Run 3 — v4_contrastive
**Date:** 2026-07-16
**Model:** Qwen 2.5 7B Instruct (Ollama)
**Prompt version:** v4_contrastive
**Goal:** Improve classification boundaries using contrastive few-shot examples and `<thought_process>` reasoning blocks before emitting YAML.

**Results (Run 20260716_191632):**
| Metric | Value |
|--------|-------|
| Precision | 0.5000 (3/6) |
| Recall | 0.3000 (3/10) |
| F1 | 0.3750 |
| Hallucination rate | 0.0000 (0/6) |
| YAML validity rate | 1.0 (6/6) |

**Observed Metric Changes:** 
F1 increased from 0.125 to 0.375. Precision reached 50%. The hallucination rate remained 0%, confirming the strict verbatim evidence constraint is working efficiently.

**Failure analysis & Lessons Learned:**
A manual breakdown of the false positives and false negatives revealed structural weaknesses in evaluation and model behavior:

1. **Name Mismatch FPs:** The evaluation harness uses exact key matching `(name::type)`. All 3 False Positives were actually semantically correct extractions with the wrong name!
   - Extracted `cache_block_operation_mechanism` vs Gold `non_coherent_agent_cbo_mechanism`.
   - Extracted `memory_access_type_implementation_specific` vs Gold `cmo_trigger_match_type`.
   *Lesson:* The model understands the parameter but applies generic, descriptive naming instead of specific, domain-derived naming.

2. **Type Confusion:** The model struggles to differentiate between `boolean` and `enumerated` types.
   - Extracted `cache_block_update_order_and_granularity` as `boolean` instead of `enumerated`.
   *Lesson:* The model needs clearer guidance that multi-valued choices (order, granularity, mechanism) are `enumerated`, not just `boolean`.

3. **Multi-Parameter Blindspot:** When a single snippet contains multiple parameters (e.g., `cache_block_size.txt` contains cache organization AND block size; `cmo_trigger_behavior.txt` contains module behavior AND match type), the model stops extracting after finding the first one.
   *Lesson:* Explicit instruction is needed to evaluate EACH candidate sentence independently and extract ALL parameters.

**Next iteration (v5/v6):** 
1. **v5_refined_contrastive:** Refine contrastive examples to include multi-parameter extraction, explicit type disambiguation (boolean vs enumerated), and stricter naming conventions.
2. **v6_decision_framework:** Introduce a highly structured Q1→Q2→Q3 decision framework to force explicit reasoning about WHO has the choice, WHETHER variability exists, and WHAT the variability axis is.

---

## Run 4 — v5_refined_contrastive
**Date:** 2026-07-17
**Model:** Qwen 2.5 7B Instruct (Ollama)
**Prompt version:** v5_refined_contrastive
**Goal:** Address naming mismatches, type confusion, and multi-parameter omissions by explicitly guiding naming conventions, defining `enumerated` vs `boolean` strictly, and demonstrating multi-parameter extraction in few-shot examples.

**Results (Run 20260717_052939):**
| Metric | Value |
|--------|-------|
| Precision | 0.4000 (4/10) |
| Recall | 0.4000 (4/10) |
| F1 | 0.4000 |
| Hallucination rate | 0.0000 (0/10) |

**Observed Metric Changes:** 
F1 increased to 0.4000, and Recall increased from 0.3000 to 0.4000. Total parameters extracted increased from 6 to 10. The multi-parameter explicit instruction worked exceptionally well — `cache_block_size.txt` perfectly extracted both parameters (size and capacity), and `wlrl_field_behavior.txt` finally extracted the boolean exception parameter.

**Failure analysis & Lessons Learned:**
- Still exhibited some naming mismatches (e.g. `cbo_zero_update_order_and_granularity` instead of `cbo_zero_atomicity_and_granularity`).
- Falsely extracted `debug_csr_access.txt` as a boolean parameter despite it being a normative "should" requirement.
- The model struggled slightly with WARL fields by over-extracting `warl_read_behavior` as an extra parameter. 

---

## Run 5 — v6_decision_framework
**Date:** 2026-07-17
**Model:** Qwen 2.5 7B Instruct (Ollama)
**Prompt version:** v6_decision_framework
**Goal:** Evaluate if forcing a strictly sequential decision framework (Q1: WHO has the choice? -> Q2: Is there variability? -> Q3: What is the axis?) inside the CoT block improves recall and classification precision compared to unstructured CoT. Includes a self-check step for verbatim evidence.

**Results (Run 20260717_053803):**
| Metric | Value |
|--------|-------|
| Precision | 0.3846 (5/13) |
| Recall | 0.5000 (5/10) |
| F1 | 0.4348 |
| Hallucination rate | 0.0000 (0/13) |

**Observed Metric Changes:** 
Highest Recall (0.5000) and F1 (0.4348) so far. `wlrl_field_behavior.txt` was perfectly extracted (both parameters), and it properly extracted `non_coherent_agent_cbo_mechanism` with exact type matching (`enumerated`). 

**Failure analysis & Lessons Learned:**
- **Regression on negative cases:** Extracted `wpri_field_behavior` (2 FPs) despite explicit rules against WPRI, indicating the Q1->Q2->Q3 framework might have overwhelmed the model's ability to retain negative rules in the system prompt.
- **Regression on type constraints:** Misclassified `cache_block_size` as `boolean` (`cache_block_size_implementation_specific`) instead of `numeric_range`. 
- **Conclusion:** Structured reasoning (V6) excels at finding parameters and resolving complex axes (WARL/WLRL) but struggles with type boundaries and negative constraints compared to V5. V5 provides a more balanced precision approach, while V6 acts as a high-recall extractor.

---

## Final Analysis: Engineering Discussion

### 1. Why certain parameters are difficult to extract
Architectural parameters in the RISC-V specification are not always explicitly labelled as "implementation-defined". 
- **Implicit variability:** Sometimes variability is implied by terms like "permitted but not required" or "may update in any order". 
- **Intermingled constraints:** Mandatory hardware behaviors ("must make them read-only zero") often sit alongside software permissions ("software should ignore"). Distinguishing WHO the instruction is directed at is difficult for LLMs without structured reasoning.
- **Complex abstractions:** CSR field behaviors (WLRL/WARL) are conceptually dense. Understanding that the variability lies in *which bit encodings the hardware chooses to support* requires deep semantic comprehension.

### 2. Why False Positives occurred
True semantic False Positives happen when the model misinterprets normative language (e.g., "should" used as a requirement for hardware). However, our analysis showed that the most common "False Positives" were actually **Evaluation Harness Artifacts**: the model successfully extracted the parameter but assigned a name (e.g., `cache_block_operation_mechanism`) that failed exact string matching with the Gold dataset (`non_coherent_agent_cbo_mechanism`).

### 3. Why False Negatives occurred
- **Premature Halting:** The model frequently stopped after extracting the first parameter in a snippet, missing subsequent parameters entirely.
- **Context Loss:** In borderline cases like WLRL field behavior, the model failed to connect the linguistic signal ("permitted but not required") with the broader hardware implication, discarding it as non-parameter text.

### 4. Remaining Limitations
- **Evaluation Brittleness:** Exact string matching for parameter names heavily penalizes models for semantic variations.
- **Dependency on Candidate Detection:** Pass 1 relies on regex trigger keywords. If a parameter is described without a standard trigger keyword (e.g., "may", "implementation-specific"), it will never reach Pass 2.

### 5. Future Improvements
- **Semantic Evaluation:** Upgrade the evaluation harness to use LLM-as-a-judge or embedding similarity to score parameter equivalence rather than strict string matching.
- **Pass 1 Recall Enhancements:** Instead of pure regex, use a lightweight, high-recall embedding classifier for Pass 1 to catch implicit parameters lacking standard trigger words.
- **Multi-Agent Debate:** Use a two-agent setup in Pass 2 where Agent A proposes extractions and Agent B critiques them against the constraints before final emission, significantly reducing type confusions and missing multi-parameters.

---

## 6. Cross-Model Analysis: Qwen 2.5 vs. Llama 3.1

As part of the hardening phase, we ran a cross-model evaluation to observe extraction differences. 

### Metrics Comparison (Relaxed Match)

| Metric | Qwen 2.5 7B | Llama 3.1 8B |
|--------|-------------|--------------|
| **Precision** | 0.5000 | TBD |
| **Recall** | 0.6000 | TBD |
| **F1 Score** | 0.5455 | TBD |
| **Hallucination Rate** | 0.0% | TBD |

### Disagreement Analysis

*Detailed disagreement cases will be recorded here based on the `generate_disagreement_report` output.*
