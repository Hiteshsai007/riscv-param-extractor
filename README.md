# RISC-V Architectural Parameter Extractor

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Apache License](https://img.shields.io/badge/License-Apache%202.0-D22128.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Inference-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![Pydantic](https://img.shields.io/badge/Pydantic-Schema%20Validation-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/latest/)
[![Linux Foundation](https://img.shields.io/badge/LFX-Coding%20Challenge-003778)](https://lfx.linuxfoundation.org/)

This repository contains my submission for the Linux Foundation (LFX) RISC-V AI-assisted Architectural Parameter Extraction coding challenge. The objective is to extract implementation-defined architectural parameters from RISC-V ISA specification snippets using prompt-engineered large language models while ensuring deterministic validation, reproducibility, and structured YAML output.

**LFX Mentorship Coding Challenge — Part II**  
**Author:** Hitesh

## Check it without trusting me

```bash
./verify.sh
# re-derives every published number offline, no model calls
```

See [CLAIM-LEDGER.md](CLAIM-LEDGER.md) for the full claim → artifact map.

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

### Example 1 — Cache Block Specification (R1 Corrected)

> **Note:** Prior versions of this README extracted `cache_capacity_and_organization` as a
> valid parameter with `confidence: high`. This was the core judgment bug identified in the
> PRD: cache capacity/organization is an implementation-specific microarchitectural detail
> but is NOT ISA-visible — no instruction's defined behavior depends on it. The corrected
> output below rejects it with reason code `NOT_ISA_VISIBLE` (R1) and a justification.

```yaml
source_file: data\raw_snippets\cache_block_size.txt
source_section: Unprivileged Spec, Cache Management Operations (CMO) §cmo
candidates_found: 1
parameters_extracted: 1
parameters:
- name: cache_block_size
  description: The size of a cache block, which is implementation-specific.
  type: numeric_range
  constraints: Must be uniform throughout the system in initial CMO extensions.
  evidence: the size of a cache block are both implementation-specific
  trigger_keyword: implementation-specific
  source_section: Unprivileged Spec, CMO §cmo
  confidence: high
  isa_visible: true
  visibility_justification: >-
    CMO instructions (CBO.ZERO, CBO.CLEAN, CBO.FLUSH, CBO.INVAL) operate on
    cache-block-sized granules. The block size determines the effective address
    range affected by a single instruction execution.
rejected_candidates:
- candidate_text: The capacity and organization of a cache
  reason: NOT_ISA_VISIBLE
  detail: >-
    Cache capacity and organization are microarchitectural details. No ISA-defined
    instruction produces different specified behavior based on cache capacity.
  isa_visible: false
  visibility_justification: >-
    No RISC-V instruction's architecturally-defined behavior depends on cache
    capacity or internal organization.
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
rejected_candidates:
- candidate_text: Software should not write anything other than legal values to such a field
  reason: CONSTRAINT_NOT_PARAMETER
  detail: >-
    This is a normative requirement directed at software ("should not"), not a
    hardware variability axis. The hardware behavior is defined by the WLRL
    field specification itself.
hallucination_flags: []
```

---

These examples are actual outputs generated by the extraction pipeline.

All outputs are automatically validated against the project's Pydantic schema before being written to disk.

Each extracted parameter includes a verbatim evidence field that must exactly match text from the original specification, providing a deterministic safeguard against hallucinations.

Invalid YAML or unsupported fields are automatically rejected and regenerated before being accepted.

---

## Verification & Auditability

Run ./verify.sh — every published number re-derives from committed artifacts.

This repository now carries the audit trail needed for offline review:
- [ground_truth.md](ground_truth.md) — pre-committed evaluation ledger with expected parameters and rejection reasons.
- [verify.sh](verify.sh) — re-derives numeric claims from committed results and gold files, then re-runs the offline validator.
- [src/validate.py](src/validate.py) — fail-closed validator for schema, evidence grounding, ISA visibility justifications, and rejection reason codes.
- [CLAIM-LEDGER.md](CLAIM-LEDGER.md) — maps every quantitative claim in this README to the result file and script that produce it.

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
2. **ISA-visibility gate:** Before schema acceptance, `extract.py` requires `isa_visible: true`, a substantive justification, and a real instruction/CSR mnemonic. The matching function in `src/isa_verification.py` is shared with `scripts/verify_isa_claims.py`, so the live gate and post-run audit use one rule.
3. **Schema validation:** 100% of outputs must pass Pydantic validation.
4. **Retry logic:** Malformed LLM output triggers retry (configurable, default 2).

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

## Evaluation Metrics (Historical Run 5: `v6_decision_framework`)

Evaluated on Set A — 10 annotated snippets (7 positive, 3 negative). Graded against the **pre-R1** gold snapshot archived at `data/gold/archive/pre_r1_fix/` (live gold was corrected in P0.1; see CLAIM-LEDGER). Re-derive with `python scripts/verify.py`.

### Decomposed Match Credit (R9)

| Metric | Exact Match | Relaxed Match (≥0.75) | Delta | Notes |
|--------|-------------|----------------------|-------|-------|
| **Precision** | 0.3846 | 0.5000 | +0.1154 | 3 matches gained by relaxed name similarity |
| **Recall** | 0.5000 | 0.6000 | +0.1000 | |
| **F1 Score** | 0.4348 | 0.5455 | +0.1107 | |
| **Hallucination Rate** | 0.0% | 0.0% | — | 100% of evidence fields are verbatim substrings |
| **YAML Validity** | 100% | 100% | — | |

**Exact match** = both parameter `name` and `type` are identical strings. **Relaxed match** = `difflib.SequenceMatcher` ratio ≥ 0.75 on normalized names + exact `type` match. See `src/eval_harness.py` for implementation.

## Evaluation Metrics (Live Unified Gate — Hardening Pass 2)

Artifacts: `results/run_20260730_152612/` (full 30, prompt `v6_decision_framework`, seed=42, temp=0, live ISA-visibility gate). Graded against **current** R1-corrected gold. Re-derive: `python scripts/compute_eval_breakdown.py --results results/run_20260730_152612`.

| Slice | **Precision** | **Recall** | **F1 Score** | **Hallucination Rate** | Notes |
|-------|---------------|------------|--------------|------------------------|-------|
| Full corpus (30) | 0.5000 | 0.1154 | 0.1875 | 0.0% | ±0.15 falsification vs historical 0.4348 **triggered** |
| Set A only (10) | 1.0000 | 0.3333 | 0.5000 | 0.0% | Same gate; gold denominator 9 after P0.1 |
| Sets B–D (20) | 0.0000 | 0.0000 | 0.0000 | 0.0% | **First evaluation of forward-registered set** |

Gold-correction delta on historical Run 5 artifacts (informational): F1 0.4348 → 0.4545 when scored under corrected gold (`scripts/verify.py`).

### Grounding vs Discovery Recall (P1.1)

| Recall Type | Prompt | Run | Set A Recall (strict) |
|-------------|--------|-----|------------------------|
| Grounding (gold names present) | `v6_decision_framework` | `results/run_20260730_160338` | **0.4444** (full Set A) / **0.6000** on name-leaked subset |
| Discovery (gold names absent) | `v8_discovery` | `results/run_20260730_162340` | **0.0000** |

Discovery extracted the right *concepts* on WLRL/CSR-trap snippets but emitted illustrative off-evaluation example names (`legal_encoding_subset`, `privileged_csr_intercept`) — exact-match recall is therefore zero. Documented in CLAIM-LEDGER / EXPERIMENTS.

### Run-to-run Variance (P1.2)

Identical config (`v6`, seed=42, temp=0) on Set A, two committed runs:

| Run | P | R | F1 |
|-----|---|---|-----|
| `results/run_20260730_160338` | 1.0000 | 0.4444 | 0.6154 |
| `results/run_20260730_161322` | 1.0000 | 0.4444 | 0.6154 |
| **Delta** | **0** | **0** | **0** |

Per-snippet parameter-name sets were identical. Under this config, single-run figures are repeatable on Set A (delta zero).

### Recall Type Disclosure (R8)

The v6 prompt includes one contrastive positive example (cache_block_size) and one negative example (WPRI) in the system prompt. The gold parameter *names* are embedded in these examples. This means the reported recall for cache_block_size and WPRI snippets measures **grounding recall** (matching against a catalogue the model has seen), not **cold discovery recall** (finding parameters the model has never been told about). For the remaining 8 snippets, no gold names appear in the prompt — those measure genuine discovery recall.

| Recall Type | Snippets (n) | Recall |
|-------------|-------------|--------|
| Grounding (gold names in prompt) | Set A / name-leaked subset | **0.4444 / 0.6000** (live v6 Set A — see table above) |
| Discovery (no gold names in prompt) | Set A via `v8_discovery` | **0.0000** (exact match; see P1.1 note) |
| **Aggregate historical (Run 5)** | **10** | **0.5000 (strict) / 0.6000 (relaxed)** |

*Live numbers separate grounding vs discovery. Historical aggregate still conflates them.*

### Confound Reporting (R10)

| Failure class | Status | Resolution |
|--------------|--------|------------|
| Parser leak (`<thought_process>` text breaking YAML capture) | **Resolved — 2026-07-30** | The parser now isolates the YAML list after leaked reasoning text. |
| Silent field-absence rejection (`isa_visible` omitted) | **Resolved — 2026-07-30** | The v6 prompt requires the field, and the gate rejects any missing/non-true value as `NOT_ISA_VISIBLE`. |
| Hallucinated self-certification (long justification with no real ISA name) | **Resolved — 2026-07-30** | `enforce_isa_visibility_gate` and `scripts/verify_isa_claims.py` now share `justification_cites_real_mnemonic`, backed by `data/riscv_isa_index.json`. |
| **Live gate bypass on generic justification (NEW — 2026-07-30)** | **Open** | Two independent live runs on `cache_block_size.txt` produced `cache_capacity_and_organization` with a generic justification. `cache_block_size` never appeared. |
| Missing live-run artifacts for `run_20260730_113320` | **Superseded — Hardening Pass 2** | Historical claim remains documentation-only. **New** committed live trees: `results/run_20260730_152612` (full 30), `160338`/`161322` (Set A variance), `162340` (discovery). |
| **Grading gold contradicts R1 doctrine for `cache_block_size` (found 2026-07-30)** | **Resolved — P0.1, 2026-07-30** | Live gold puts `cache_capacity_and_organization` in `rejected_candidates` / `NOT_ISA_VISIBLE`. Archive at `data/gold/archive/pre_r1_fix/`. |
| Live acceptance re-test of the strict CMO rule (2026-07-30, arena sandbox) | **Blocked in arena; live-validated on maintainer machine (2026-07-30)** | Arena: no Ollama / registries / RAM. Local: Ollama `qwen2.5:7b-instruct` produced committed `isa_visible` artifacts. `cache_block_size` live extraction still yields 0 accepted params (both candidates `NOT_ISA_VISIBLE`) — gate fires; model does not recover the true positive. |
| **ISA-index vocabulary gap → systematic false rejections at scale (found 2026-07-30)** | **Resolved — pre-registration fix, 2026-07-30** | Offline audit of all ground-truth files found **12 of 18 forward-registered `isa_visible: true` justifications could never pass the shared mnemonic check**: they cite real RISC-V names (VSETVLI, MARCHID, MIMPID, MVENDORID, MHPMCOUNTER3, PMPCFG/PMPADDR) absent from the checked-in index (44 instructions / 40 CSRs — no vector, ID, PMP, or counter CSRs). Over the expanded corpus, the live gate would have rejected correct parameters regardless of model quality — a reference-vocabulary bug masquerading as a model failure. Fixed *before any live run*: `data/riscv_isa_index.json` expanded to 48 instructions / 267 CSRs (real mnemonics only; CMO remains excluded) and the 12 GT justifications rewritten to cite indexed mnemonics, names/types unchanged. Published metrics unaffected (grading is by `data/gold` name+type on the 10-snippet evaluated set only). |

The origin story took three iterations to close: first the parser leak was fixed, then the missing-field rejection was made explicit, and finally the live gate was unified with the verifier after a fabricated cache-capacity justification passed the length-only gate. These are closed failure modes, not remaining caveats; the historical runs above remain evidence of how they were found."

### Cross-Model Comparison

| Metric (Relaxed) | Qwen 2.5 7B | Llama 3.1 8B |
|------------------|-------------|--------------|
| Precision        | 0.0000      | 0.0000 |
| Recall           | 0.0000      | 0.0000 |
| F1               | 0.0000      | 0.0000 |
| Hallucination    | 0.0%        | 0.0% |

*The latest run for cross-model evaluation showed catastrophic format instruction breakdown on both models when using the v6 prompt. Neither model was able to extract parameters because the CoT text leaked into the YAML tags, producing 0% recall across the board. See Confound Reporting above.*

### Evaluation Limitations (R12 — with falsification conditions)

1. **Small N (10 snippets) — falsified.** Expanding to 30 snippets changed live F1 from historical 0.4348 to **0.1875** (Δ > 0.15). Historical Set-A F1 does not generalize; Sets B–D first-eval F1 = 0.0000.

2. **Grounding vs discovery — now separated (P1.1).** Discovery (`v8`) Set A exact-match recall = 0.0000 vs grounding Set A 0.4444 (Δ > 0.1). Historical aggregate overstated cold discovery.

3. **Run-to-run variance measured (P1.2).** Two identical Set A runs (`160338` vs `161322`) → ΔP=ΔR=ΔF1=0. Under this config, single-run Set A figures are repeatable.

### Development Mistakes (R13 — honest disclosure)

- **2026-07-21:** The initial cross-model comparison (`scripts/run_cross_model.py`) was committed and advertised in README before the Llama run completed. All Llama metrics were reported as `TBD` placeholders, then corrected to `N/A (Failed)` after the run timed out. The scaffolding was sound but the claim of "cross-model evaluation" was premature.
- **2026-07-21:** `prompts/v8_final_udb_alignment.md` was committed as a near-duplicate of v7, then deleted the same day. It was never run against the gold set but briefly appeared in git history.
- **2026-07-28:** `scripts/verify.py` was committed with a bug — it accessed `report["precision"]` instead of `report["aggregate"]["precision"]`, meaning the reproducibility verification script would crash if run. Fixed in this commit.

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

# Verify all published metrics match committed artifacts (zero API calls)
python scripts/verify.py
python scripts/verify.py --list  # Show which claims are checkable
```

## Upstream Contribution Status (R14)

This repository is a standalone coding challenge submission for the LFX Mentorship. As of 2026-07-29:

- **No upstream PR** has been opened against `riscv-software-src/riscv-unified-db`.
- The `scripts/generate_spec_tags.py` tool produces UDB-format YAML files and mock patches, but these have not been submitted upstream.
- The `data/udb_reference/` files were fetched from the public UDB repo for cross-referencing; no modifications were made.
- Cross-referencing against UDB is for validation provenance, not a claim of contribution to the UDB project.

## License

Apache 2.0
