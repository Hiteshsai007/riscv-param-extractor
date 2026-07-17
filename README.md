# RISC-V Architectural Parameter Extractor

**LFX Mentorship Coding Challenge — Part II**
**Author:** Hitesh

AI-assisted extraction of architectural parameters from RISC-V ISA specifications using a two-pass LLM pipeline with mechanical hallucination detection.

## Coding Challenge Deliverables

### Deliverable 1 — LLM Details
- **Model Name:** Qwen 2.5 7B Instruct
- **Model Version:** `qwen2.5:7b-instruct`
- **Context Length:** 8,192 tokens
- **Temperature:** 0.0 (Deterministic extraction)
- **Seed:** 42
- **Runtime:** Locally executed via Ollama engine. Run metrics (execution time) are logged automatically to console and `summary.yaml`.

### Deliverable 2 — Prompt Engineering
- **Prompt Evolution:** Progressed from zero-shot (`v1_baseline`) to few-shot (`v2`), Chain of Thought with contrastive examples (`v4_contrastive`), and finally a structured Q1→Q2→Q3 Decision Framework (`v6_decision_framework`).
- **Prompt Refinement:** Iterations were driven by failure analysis on the gold dataset, resolving issues like type confusion (`boolean` vs `enumerated`) and multi-parameter extraction halting.
- **Hallucination Mitigation Strategy:** A strict, mechanical anti-hallucination gate is implemented in Python (`validate_yaml.py`). The LLM must output an `evidence` field, which is checked to ensure it is a verbatim, character-for-character substring of the source text. If not, it is flagged as a hallucination.
- **Lessons Learned:** Instruction-tuned 7B models strictly require 1-shot formatting templates for Pydantic schema compliance. Explicit contrastive examples are essential for boundary detection. The complete iteration log is in `EXPERIMENTS.md`.

### Deliverable 3 — Results
- **YAML Output Format:** Validated by a strict Pydantic schema (`schema/parameter_schema.py`).
- **Required Fields:** `name`, `description`, `type`, `constraints`, `evidence`, `trigger_keyword`, `source_section`, `confidence`.
- **Evaluation Metrics:** Evaluated for Precision, Recall, F1, Hallucination Rate, and YAML Validity.
- **Example Output:**
```yaml
- name: "cache_block_size"
  description: "The size of a cache block, which is implementation-specific."
  type: "numeric_range"
  constraints: "Must be uniform throughout the system in initial CMO extensions."
  evidence: "the size of a cache block are both implementation-specific"
```

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd riscv-param-extractor
pip install -r requirements.txt

# 2. Verify schema and tests pass
python -m pytest tests/ -v

# 3. Check LLM connectivity (requires Ollama running)
python -m src.cli --health-check --config config/default.yaml

# 4. Run extraction on example snippets
python -m src.cli --input data/raw_snippets/ --config config/default.yaml

# 5. Evaluate results against gold labels
python -m src.eval_harness --results results/<run_dir>/ --gold data/gold/ --snippets data/raw_snippets/
```

## Architecture

```
Input Snippet → [Pass 1: Regex Candidate Detection] → Candidate Sentences
                                                            ↓
                                                    [Pass 2: LLM Classification + Extraction]
                                                            ↓
                                                    [Schema Validation (Pydantic)]
                                                            ↓
                                                    [Evidence Grounding Check (verbatim substring)]
                                                            ↓
                                                    Validated Parameters (YAML)
```

### Two-Pass Pipeline

- **Pass 1 (Deterministic):** Regex-based trigger keyword matching identifies candidate sentences. No LLM call — fully reproducible, free to run.
- **Pass 2 (LLM):** Each candidate is classified as `parameter | software_permission | mandatory_behavior | structural_convention | architectural_constant`. Only genuine parameters are extracted as structured YAML.

### Anti-Hallucination Gates

1. **Verbatim evidence check:** Every parameter's `evidence` field must be an exact substring of the source text. Mechanical — no LLM judgment needed.
2. **Schema validation:** 100% of outputs must pass Pydantic validation.
3. **Retry logic:** Malformed LLM output triggers retry (configurable, default 2).

## Project Structure

```
riscv-param-extractor/
├── README.md
├── EXPERIMENTS.md              # Prompt iteration log with metrics
├── requirements.txt
├── config/
│   ├── default.yaml            # Generation params, model config
│   └── models/                 # Per-model configs
├── prompts/
│   ├── v1_baseline.md          # Current prompt version
│   └── CHANGELOG.md            # Prompt version history
├── schema/
│   └── parameter_schema.py     # Pydantic models (source of truth)
├── src/
│   ├── cli.py                  # CLI entry point
│   ├── extract.py              # Main pipeline orchestrator
│   ├── candidate_detector.py   # Pass 1: deterministic regex
│   ├── llm_client.py           # LLM abstraction (Ollama + API)
│   ├── prompt_manager.py       # Prompt loading and formatting
│   ├── validate_yaml.py        # Schema + evidence validation
│   └── eval_harness.py         # Precision/recall/hallucination metrics
├── data/
│   ├── raw_snippets/           # Text from ISA manual chapters
│   └── gold/                   # Hand-labeled expected outputs
│       ├── positive_cases/
│       └── negative_cases/
├── results/                    # Pipeline output (per-run directories)
└── tests/
    ├── test_schema.py
    └── test_evidence.py
```

## Configuration

All generation parameters are externalized in `config/default.yaml`:

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| temperature | 0.0 | Extraction is retrieval, not creative generation |
| seed | 42 | Fixed for reproducibility |
| max_tokens | 4096 | Sized for schema × ~10 candidates |
| top_p | 1.0 | Irrelevant at temperature=0 |
| repetition_penalty | 1.0 | No penalty — technical terms must not be distorted |

## Models

| Model | Role | Config |
|-------|------|--------|
| Qwen 2.5 7B Instruct | Primary | `config/models/qwen2_5.yaml` |
| Llama 3.1 8B Instruct | Comparison | `config/models/llama3_1.yaml` |

**Inference framework:** Ollama (local). Install from [ollama.ai](https://ollama.ai).

```bash
# Pull models
ollama pull qwen2.5:7b-instruct
ollama pull llama3.1:8b-instruct-q4_K_M
```

## Evaluation Metrics

| Metric | Target | Method |
|--------|--------|--------|
| Precision | ≥ 0.85 | Extracted ∩ gold / extracted |
| Recall | ≥ 0.80 | Extracted ∩ gold / gold |
| Hallucination rate | ≤ 5% | % evidence fields failing substring check |
| YAML validity | 100% | % outputs passing Pydantic on first attempt |
| Reproducibility | ≥ 95% | 3× repeated runs, field-level diff |

**Evaluation Limitations:**
- Precision and Recall currently use deterministic exact matching against gold labels (`name::type`).
- Semantically equivalent parameter names (e.g., `cache_block_operation_mechanism` vs. `non_coherent_agent_cbo_mechanism`) are counted as mismatches (causing 1 FP and 1 FN).
- Therefore, the reported metrics are highly conservative.
- This design was intentionally chosen to guarantee reproducibility and deterministic evaluation without relying on a subjective LLM judge.

## Reproducing Results

Every run generates a `manifest.yaml` recording exact configuration. To reproduce:

```bash
# Use the same config that generated the result
python -m src.cli --input data/raw_snippets/ --config results/<run_dir>/manifest.yaml
```

## License

Apache 2.0
