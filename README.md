# RISC-V Architectural Parameter Extractor

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Apache License](https://img.shields.io/badge/License-Apache%202.0-D22128.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Inference-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![Pydantic](https://img.shields.io/badge/Pydantic-Schema%20Validation-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/latest/)
[![Linux Foundation](https://img.shields.io/badge/LFX-Coding%20Challenge-003778)](https://lfx.linuxfoundation.org/)

This repository contains my submission for the Linux Foundation (LFX) RISC-V AI-assisted Architectural Parameter Extraction coding challenge. The objective is to extract implementation-defined architectural parameters from RISC-V ISA specification snippets using prompt-engineered large language models while ensuring deterministic validation, reproducibility, and structured YAML output.

**LFX Mentorship Coding Challenge — Part II**  
**Author:** Hitesh

## Challenge Deliverable Map

| Challenge Requirement | Repository Location |
|-----------------------|---------------------|
| **1. LLM Details** | [README → Deliverable 1](#deliverable-1) |
| **2. Prompt Files** | [prompts/](prompts/) |
| **3. Prompt Engineering Journey** | [EXPERIMENTS.md](EXPERIMENTS.md) |
| **4. Hallucination Mitigation** | [README → Deliverable 2](#deliverable-2) + [EXPERIMENTS.md](EXPERIMENTS.md) |
| **5. Example YAML Outputs** | [results/](results/) / [README → Example YAML Output](#example-yaml-output) |
| **6. Source Code** | [src/](src/) |

## Coding Challenge Deliverables


<a id="deliverable-1"></a>
### Deliverable 1 — LLM Details
- **Model Name:** Qwen 2.5 7B Instruct
- **Model Version:** `qwen2.5:7b-instruct`
- **Context Length:** 8,192 tokens
- **Temperature:** 0.0 (Deterministic extraction)
- **Seed:** 42
- **Runtime:** Locally executed via Ollama engine. Run metrics (execution time) are logged automatically to console and `summary.yaml`.

<a id="deliverable-2"></a>
### Deliverable 2 — Prompt Engineering Journey
- **Prompt Engineering Journey:** Progressed from zero-shot (`v1_baseline`) to few-shot (`v2`), Chain of Thought with contrastive examples (`v4_contrastive`), and a structured Q1→Q2→Q3 Decision Framework (`v6_decision_framework`). *Note: `v6` remains the evaluated best; `v7_lfx_hardening` is currently an unevaluated draft incorporating cross-model lessons.*
- **Prompt Refinement:** Iterations were driven by failure analysis on the gold dataset, resolving issues like type confusion (`boolean` vs `enumerated`) and multi-parameter extraction halting.
- **Hallucination Mitigation Strategy:** A strict, deterministic hallucination validation gate is implemented in Python (`validate_yaml.py`). The LLM must output an `evidence` field, which is checked to ensure it is a verbatim, character-for-character substring of the source text. If not, it is flagged as a hallucination.
- **Lessons Learned:** Instruction-tuned 7B models strictly require 1-shot formatting templates for Pydantic schema compliance. Explicit contrastive examples are essential for boundary detection. The complete iteration log is in `EXPERIMENTS.md`.

### Deliverable 3 — Results
- **YAML Output Format:** Validated by a strict Pydantic schema (`schema/parameter_schema.py`).
- **Required Fields:** `name`, `description`, `type`, `constraints`, `evidence`, `trigger_keyword`, `source_section`, `confidence`.
- **Evaluation Metrics:** Evaluated for Precision, Recall, F1, Hallucination Rate, and YAML Validity.

<a id="example-yaml-output"></a>
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

## Evaluation Metrics (Run 5: `v6_decision_framework` + LFX Hardening)

Currently evaluated on 10 annotated snippets (7 positive, 3 negative). We evaluate strictly (exact string match on both parameter name and type) and relaxed (normalized string similarity $\ge$ 0.75 on name, exact on type).

| Metric | Strict (Qwen) | Relaxed (Qwen) | Notes |
|--------|---------------|----------------|-------|
| **Precision** | 0.3846 | 0.5000 | Lowered by spec ambiguity (e.g., CBO update mechanisms). Relaxed matching handles slight name phrasing variations. |
| **Recall** | 0.5000 | 0.6000 | Misses implicit parameters not directly tied to keywords. |
| **F1 Score** | 0.4348 | 0.5455 | Good baseline for a zero-shot/few-shot system without external RAG. |
| **Hallucination Rate** | 0.0% | 0.0% | 100% of extracted evidence fields are verbatim substrings of the source. |
| **YAML Validity** | 100% | 100% | Pipeline produces perfectly conforming JSON/YAML on the first attempt. |

### Evaluation Limitations

- **Small N:** 10 snippets is a very small sample size.
- **Strict vs. Relaxed Matching:** Strict matching penalizes the LLM for valid syntactic variations of parameter names (e.g., `cache_capacity` vs `cache_capacity_and_organization`). The relaxed metric (normalized string similarity $\ge$ 0.75) accommodates phrasing differences while keeping type-matching strict.

## Cross-Model Comparison

To ensure the pipeline is robust to different base models, we evaluate using both Qwen 2.5 7B and Llama 3.1 8B. See `EXPERIMENTS.md` for a detailed breakdown of cross-model disagreements.

| Metric (Relaxed) | Qwen 2.5 7B | Llama 3.1 8B |
|------------------|-------------|--------------|
| Precision        | 0.5000      | N/A (Failed) |
| Recall           | 0.6000      | N/A (Failed) |
| F1               | 0.5455      | N/A (Failed) |
| Hallucination    | 0.0%        | N/A (Failed) |

*Note: The Llama 3.1 8B evaluation (n=4 reduced snippet set) consistently failed due to local Ollama API timeouts (300s/1200s) and 500 Internal Server Errors, demonstrating hardware/infrastructure limitations when running cross-model comparisons locally. Scaffolding is complete, but data remains unavailable until run on a larger instance.*

## UDB Grounding

The `data/gold/` set has been cross-referenced against actual [RISC-V Unified Database (UDB)](https://github.com/riscv-software-src/riscv-unified-db) parameter entries. This provides real-world provenance for the extraction targets. See `data/udb_reference/README.md` and `data/gold/udb_crossref.yaml` for details.

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
