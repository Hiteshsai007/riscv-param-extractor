# RISC-V Architectural Parameter Extractor

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Apache License](https://img.shields.io/badge/License-Apache%202.0-D22128.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Inference-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![Pydantic](https://img.shields.io/badge/Pydantic-Schema%20Validation-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/latest/)
[![Linux Foundation](https://img.shields.io/badge/LFX-Coding%20Challenge-003778)](https://lfx.linuxfoundation.org/)

This repository contains my submission for the Linux Foundation (LFX) RISC-V AI-assisted Architectural Parameter Extraction coding challenge. The objective is to extract implementation-defined architectural parameters from RISC-V ISA specification snippets using prompt-engineered large language models while ensuring deterministic validation, reproducibility, and structured YAML output.

**LFX Mentorship Coding Challenge — Part II**  
**Author:** Hitesh

## Coding Challenge Deliverables

### Deliverable 1 — LLM Details
- **Model Name:** Qwen 2.5 7B Instruct
- **Model Version:** `qwen2.5:7b-instruct`
- **Context Length:** 8,192 tokens
- **Temperature:** 0.0 (Deterministic extraction)
- **Seed:** 42
- **Runtime:** Locally executed via Ollama engine. Run metrics (execution time) are logged automatically to console and `summary.yaml`.

### Deliverable 2 — Prompt Engineering Journey
- **Prompt Engineering Journey:** Progressed from zero-shot (`v1_baseline`) to few-shot (`v2`), Chain of Thought with contrastive examples (`v4_contrastive`), and finally a structured Q1→Q2→Q3 Decision Framework (`v6_decision_framework`).
- **Prompt Refinement:** Iterations were driven by failure analysis on the gold dataset, resolving issues like type confusion (`boolean` vs `enumerated`) and multi-parameter extraction halting.
- **Hallucination Mitigation Strategy:** A strict, deterministic hallucination validation gate is implemented in Python (`validate_yaml.py`). The LLM must output an `evidence` field, which is checked to ensure it is a verbatim, character-for-character substring of the source text. If not, it is flagged as a hallucination.
- **Lessons Learned:** Instruction-tuned 7B models strictly require 1-shot formatting templates for Pydantic schema compliance. Explicit contrastive examples are essential for boundary detection. The complete iteration log is in `EXPERIMENTS.md`.

### Deliverable 3 — Results
- **YAML Output Format:** Validated by a strict Pydantic schema (`schema/parameter_schema.py`).
- **Required Fields:** `name`, `description`, `type`, `constraints`, `evidence`, `trigger_keyword`, `source_section`, `confidence`.
- **Evaluation Metrics:** Evaluated for Precision, Recall, F1, Hallucination Rate, and YAML Validity.

# Example YAML Output

### Example 1 — Cache Block Specification
```yaml
source_file: data\raw_snippets\cache_block_size.txt
source_section: Unprivileged Spec, Cache Management Operations (CMO) §cmo
candidates_found: 1
parameters_extracted: 2
parameters:
- name: cache_block_size
  description: The size of a cache block, which is implementation-specific.
  type: numeric_range
  constraints: Must be uniform throughout the system in initial CMO extensions.
  evidence: the size of a cache block are both implementation-specific
  trigger_keyword: implementation-specific
  source_section: Unprivileged Spec, CMO §cmo
  confidence: high
- name: cache_capacity_and_organization
  description: The capacity and organization of a cache, which varies across implementations.
  type: enumerated
  constraints: null
  evidence: The capacity and organization of a cache and the size of a cache block
    are both implementation-specific
  trigger_keyword: implementation-specific
  source_section: Unprivileged Spec, CMO §cmo
  confidence: high
rejected_candidates: []
hallucination_flags: []
```

### Example 2 — CSR Specification
```yaml
source_file: data\raw_snippets\wlrl_field_behavior.txt
source_section: Privileged Spec, CSR Field Specifications §priv-csrs — WLRL
candidates_found: 3
parameters_extracted: 2
parameters:
- name: wlrl_supported_values
  description: WLRL CSR fields specify behavior for only a subset of possible bit
    encodings, with the implementation defining which values are legal.
  type: field_behavior
  constraints: Software should not write illegal values.
  evidence: Some read/write CSR fields specify behavior for only a subset of possible
    bit encodings, with other bit encodings reserved. Software should not write anything
    other than legal values to such a field, and should not assume a read will return
    a legal value unless the last write was of a legal value, or the register has
    not been written since another operation (e.g., reset) set the register to a legal
    value.
  trigger_keyword: WLRL
  source_section: Privileged Spec, CSR Field Specifications §priv-csrs
  confidence: high
- name: wlrl_illegal_write_exception
  description: Whether the implementation raises an illegal-instruction exception
    when software writes a non-supported value to a WLRL field.
  type: boolean
  constraints: Permitted but not required — implementation choice.
  evidence: Implementations are permitted but not required to raise an illegal-instruction
    exception if an instruction attempts to write a non-supported value to a WLRL
    field.
  trigger_keyword: permitted but not required
  source_section: Privileged Spec, CSR Field Specifications §priv-csrs
  confidence: high
rejected_candidates: []
hallucination_flags: []
```

---

These examples are actual outputs generated by the extraction pipeline.

All outputs are automatically validated against the project's Pydantic schema before being written to disk.

Each extracted parameter includes a verbatim evidence field that must exactly match text from the original specification, providing a deterministic safeguard against hallucinations.

Invalid YAML or unsupported fields are automatically rejected and regenerated before being accepted.

---

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

### Deterministic Hallucination Validation

1. **Verbatim evidence check:** Every parameter's `evidence` field must be an exact substring of the source text. Deterministic — no LLM judgment needed.
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
| Llama 3.1 8B Instruct | Alternative Evaluation Model | `config/models/llama3_1.yaml` |

**Inference framework:** Ollama (local). Install from [https://ollama.com](https://ollama.com).

```bash
# Pull models
ollama pull qwen2.5:7b-instruct
ollama pull llama3.1:8b-instruct-q4_K_M
```

## Evaluation Metrics

The following metrics represent the actual measured performance from the best-performing iteration (**v6_decision_framework**, Run 5):

| Metric | Measured Result | Notes |
|:---|:---|:---|
| **Precision** | 0.3846 (5/13) | Measured as the ratio of correct parameters (TP) to all extracted parameters (TP + FP) using exact matching. |
| **Recall** | 0.5000 (5/10) | Measured as the ratio of correct parameters (TP) to all parameters in the gold dataset (TP + FN) using exact matching. |
| **F1 Score** | 0.4348 | The harmonic mean of Precision and Recall. |
| **YAML Validity** | 100% (13/13) | Confirmed via mechanical validation of all generated files against the Pydantic schema prior to disk write. |
| **Hallucination Rate** | 0.0000 (0/13) | Percentage of extracted parameters whose `evidence` field failed the verbatim substring matching check. |
| **Execution Method** | Local Inference | Executed deterministically using Ollama (`qwen2.5:7b-instruct`) with `temperature: 0.0` and `seed: 42`. |

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
