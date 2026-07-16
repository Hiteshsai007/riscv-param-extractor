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

## v4_selfcheck.md — Self-Check Step (Planned)

**Planned change:** Add a self-verification step: "Before finalizing each parameter, verify that your evidence string appears verbatim in the source text. If it does not, remove that parameter from your output."

**Rationale:** Force the model to self-audit, catching evidence hallucinations before output.
