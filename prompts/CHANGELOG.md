# Prompt Changelog

All prompt versions, their changes, rationale, and resulting metric deltas.

## v1_baseline.md — Zero-shot Baseline (2026-07-16)

**Change:** Initial prompt with:
- Role definition (RISC-V ISA specification analyst)
- Classification taxonomy (parameter / software_permission / mandatory_behavior / structural_convention / architectural_constant)
- Output schema specification
- Verbatim evidence requirement
- "When uncertain, err on the side of NOT extracting" instruction

**Rationale:** Establish a baseline before adding few-shot examples. This measures how well instruction-following alone handles the three-way classification problem.

**Expected weaknesses:**
- Likely to have lower recall (conservative by design)
- May struggle with borderline cases without contrastive examples
- Evidence field may not always be verbatim (common LLM failure mode)

**Metrics:** _TBD — will be populated after first gold-set run_

---

## v2_fewshot.md — Contrastive Few-Shot (Planned)

**Planned change:** Add 3 contrastive pairs (positive/negative) to the system prompt.

**Rationale:** Models discriminate far better from contrastive pairs than from positive examples alone. Each positive example paired with a near-miss negative that looks similar but is NOT a parameter.

---

## v3_negative_examples.md — Explicit Evidence Instruction (Planned)

**Planned change:** Add explicit instruction: "If the evidence string you are about to emit does not appear character-for-character in the source text, do NOT emit the parameter."

**Rationale:** Close the hallucination loophole where models paraphrase evidence.

---

## v4_contrastive.md — Chain of Thought and Contrastive Examples (2026-07-16)

**Change:** Added a `<thought_process>` reasoning block requirement and 4 contrastive few-shot examples showing positive extractions vs negative (non-parameter) cases.

**Rationale:** The model struggled to classify parameters correctly. By showing examples of what IS and IS NOT a parameter alongside explicit reasoning steps, the model should better understand the boundaries of hardware variability.

**Metrics:** 
- F1: 0.375
- Precision: 0.50
- Recall: 0.30

---

## v5_refined_contrastive.md — Multi-Parameter and Disambiguation Refinement (2026-07-17)

**Change:** 
- Clarified type definitions (`enumerated` vs `boolean`).
- Added explicit instruction to extract ALL parameters in a snippet.
- Guided naming conventions toward specific, domain-derived names.
- Expanded contrastive examples to showcase multi-parameter extraction from a single snippet and a WPRI negative example.

**Rationale:** Analysis of v4 results showed the model confusing `boolean` and `enumerated` types, frequently stopping after extracting the first parameter in a snippet (missing the rest), and generating generic parameter names that caused false positives in string-match evaluations.

---

## v6_decision_framework.md — Structured Decision Framework (2026-07-17)

**Change:** Introduced a strict sequential Q1→Q2→Q3 decision framework inside the `<thought_process>` block:
1. WHO has the choice?
2. Is there genuine variability?
3. What is the variability axis?
Added a self-verification step for verbatim evidence strings.

**Rationale:** Unstructured Chain-of-Thought still led to context loss in borderline cases. By forcing the model to explicitly answer the three core questions defining an architectural parameter, we aim to mechanically guide its reasoning toward higher precision and recall.
