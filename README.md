<div align="center">

# RISC-V Architectural Parameter Extractor

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Apache License](https://img.shields.io/badge/License-Apache%202.0-D22128.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Inference-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![Pydantic](https://img.shields.io/badge/Pydantic-Schema%20Validation-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/latest/)
[![Linux Foundation](https://img.shields.io/badge/LFX-Coding%20Challenge-003778)](https://lfx.linuxfoundation.org/)
[![Hallucination Rate](https://img.shields.io/badge/Hallucination%20Rate-0%25-2E7D52)](#results)
[![Reproducible](https://img.shields.io/badge/Reproducible-Offline%20%E2%80%A2%20Zero%20API%20Calls-1F3A5F)](#check-it-without-trusting-me)

**LFX Mentorship Coding Challenge — Part II** · **Author:** [Hitesh](https://github.com/Hiteshsai007)

Local, auditable extraction of implementation-defined RISC-V architectural parameters.
Every bold number re-derives from committed artifacts — no API keys, no model calls.

</div>

---

## Contents

- [Check it without trusting me](#check-it-without-trusting-me)
- [What this is](#what-this-is-one-screen)
- [Coding challenge exam (2 snippets)](#coding-challenge-exam-2-snippets)
- [Architecture](#architecture)
- [Extended evaluation (30 snippets) & key findings](#extended-evaluation-30-snippets--key-findings)
- [Results](#results)
- [Challenge deliverable map](#challenge-deliverable-map)
- [Claims NOT being made](#claims-not-being-made)
- [Quick start](#quick-start)
- [Deliverable 1 — LLM details](#deliverable-1--llm-details)
- [Deliverable 2 — Prompts & hallucination mitigation](#deliverable-2--prompts--hallucination-mitigation)
- [Project structure](#project-structure)
- [License](#license)

---

## Check it without trusting me

```bash
./verify.sh
# Windows:  powershell -File .\verify.ps1
# Optional: ./verify.sh --list
```

Offline. No API keys. No model calls. Re-derives every published number from
committed artifacts and fails if any disagree.

| Check | Command / artifact |
|-------|--------------------|
| Metrics re-derived | [`scripts/verify.py`](scripts/verify.py) |
| GT predates results | [`scripts/check_commit_order.py`](scripts/check_commit_order.py) |
| Evidence verbatim | [`src/validate_yaml.py`](src/validate_yaml.py) |
| Bad fixtures fail closed | [`tests/bad_examples/`](tests/bad_examples/) |
| Prompt leakage | [`scripts/check_prompt_leakage.py`](scripts/check_prompt_leakage.py) |
| Claim → artifact map | [`CLAIM-LEDGER.md`](CLAIM-LEDGER.md) |

---

## What this is (one screen)

| | |
|---|---|
| **Input** | 30 ISA snippets (10 Set A + 20 forward-registered B–D) |
| **Output** | accepted parameters + rejected candidates with reason codes |
| **Model** | Qwen 2.5 7B Instruct (local Ollama), T=0, seed=42 |
| **Gates** | verbatim evidence · ISA-visibility · Pydantic · commit-order |
| **Primary live run** | [`results/run_qwen_fast/`](results/run_qwen_fast/) (post-fix §8, unified gate) |
| **Previous live run** | [`results/run_20260730_152612/`](results/run_20260730_152612/) (pre-fix unified gate) |
| **Historical baseline** | [`results/run_20260717_053803/`](results/run_20260717_053803/) (**predates** `isa_visible` fields) |

---

## Coding challenge exam (2 snippets)

The strict 2-snippet exam designed to test the parameter extraction pipeline against the exact LFX coding challenge requirements.

- **Exam surface:** [`challenge/`](challenge/)
- **Expected yield:** `cache_block_size` (ISA-visible; `CBO.*` granules) from the CMO snippet; **zero** parameters from the CSR snippet.
- **Results & predictions:** The pure prompt (zero evaluation-snippet answer strings) successfully extracted 0 parameters from the CSR snippet, but failed to extract `cache_block_size` because a 7B model lacks the explicit zero-shot knowledge to cite `CBO.ZERO` without few-shot guidance. This falsified our prediction and proved the strictness of the ISA gate. See [`challenge/README.md`](challenge/README.md) for the full failure/decision table.
- **Pure-prompt claim:** guarded by [`scripts/check_prompt_leakage.py`](scripts/check_prompt_leakage.py).

---

## Architecture

Rendered SVG: [`docs/pipeline-architecture.svg`](docs/pipeline-architecture.svg)

```mermaid
flowchart TD
  subgraph INGEST[" "]
    S["ISA snippet"]:::input --> P1["Pass 1 — regex candidates"]:::process
    P1 --> P2["Pass 2 — LLM extract"]:::process
  end
  subgraph GATES[" "]
    P2 --> V1["Gate 1 — Pydantic schema"]:::gate
    V1 --> V2["Gate 2 — verbatim evidence"]:::gate
    V2 --> V3["Gate 3 — ISA-visibility"]:::gate
  end
  V3 --> OUT["Accepted + rejected YAML"]:::output
  GT["Precommitted GT / gold"]:::input -.-> EVAL["eval_harness"]:::output
  OUT --> EVAL
  EVAL --> M["P / R / F1 / hallucination"]:::output
  M --> VER["./verify.sh"]:::output

  classDef input fill:#EAF0F6,stroke:#1F3A5F,color:#1F3A5F,stroke-width:1.5px
  classDef process fill:#ffffff,stroke:#1F3A5F,color:#1F3A5F,stroke-width:1.5px
  classDef gate fill:#FBF0E2,stroke:#C1710D,color:#7A4A08,stroke-width:1.5px
  classDef output fill:#E9F5EE,stroke:#2E7D52,color:#1E5B3A,stroke-width:1.5px
  style INGEST fill:#F7F9FB,stroke:#C7CEDA,stroke-width:1px
  style GATES fill:#FEFBF6,stroke:#EAD3AF,stroke-width:1px
```

**Legend:** <img src="https://img.shields.io/badge/-input%2Foutput-EAF0F6?style=flat-square&labelColor=EAF0F6&color=1F3A5F" height="16"/> ingestion & artifacts &nbsp;·&nbsp; <img src="https://img.shields.io/badge/-process-ffffff?style=flat-square&labelColor=ffffff&color=1F3A5F" height="16"/> pipeline steps &nbsp;·&nbsp; <img src="https://img.shields.io/badge/-gate-FBF0E2?style=flat-square&labelColor=FBF0E2&color=C1710D" height="16"/> validation gates &nbsp;·&nbsp; <img src="https://img.shields.io/badge/-result-E9F5EE?style=flat-square&labelColor=E9F5EE&color=2E7D52" height="16"/> evaluation & verification

### Commit-order / measurement integrity

```mermaid
flowchart TD
  GT["ground_truth + gold committed first"]:::input -.-> R1["Historical run_20260717"]:::process
  GT -.-> R2["Live unified-gate run_20260730_152612"]:::process
  R2 --> BD["Set A + Sets B–D breakdown"]:::gate
  R2 --> VAR["Variance pair 160338 vs 161322"]:::gate
  R2 --> DISC["Discovery run 162340"]:::gate
  BD --> LEDGER["CLAIM-LEDGER.md"]:::output
  VAR --> LEDGER
  DISC --> LEDGER
  LEDGER --> VERIFY["./verify.sh re-derives all numbers"]:::output

  classDef input fill:#EAF0F6,stroke:#1F3A5F,color:#1F3A5F,stroke-width:1.5px
  classDef process fill:#ffffff,stroke:#1F3A5F,color:#1F3A5F,stroke-width:1.5px
  classDef gate fill:#FBF0E2,stroke:#C1710D,color:#7A4A08,stroke-width:1.5px
  classDef output fill:#E9F5EE,stroke:#2E7D52,color:#1E5B3A,stroke-width:1.5px
```

`scripts/check_commit_order.py` enforces that ground truth / gold commit **before** results for each snippet.

| Gate | Blocks | Code |
|------|--------|------|
| Pass 1 regex | Non-trigger text never reaches the LLM | [`src/candidate_detector.py`](src/candidate_detector.py) |
| Verbatim evidence | Paraphrased / fabricated quotes | [`src/validate_yaml.py`](src/validate_yaml.py) |
| ISA-visibility | Microarchitectural noise without a real mnemonic | [`src/isa_verification.py`](src/isa_verification.py) (shared by live `extract.py` + audit) |
| Pydantic | Missing / illegal fields | [`schema/parameter_schema.py`](schema/parameter_schema.py) |
| Commit-order | Post-hoc label editing | [`scripts/check_commit_order.py`](scripts/check_commit_order.py) |

---

## Extended evaluation (30 snippets) & key findings

The extended 30-snippet evaluation surface tests the pipeline on a wider variety of texts.

1. **Gold R1 contradiction fixed — capacity is `NOT_ISA_VISIBLE`.**
   Live gold rejects `cache_capacity_and_organization`; pre-correction snapshot kept for historical re-derivation —
   [`data/gold/positive_cases/cache_block_size.yaml`](data/gold/positive_cases/cache_block_size.yaml),
   [`data/gold/archive/pre_r1_fix/`](data/gold/archive/pre_r1_fix/).

2. **Forward registration falsified generalization.**
   Post-fix full-corpus F1 **0.2353**; Sets B–D first-eval F1 **0.0000**. Historical Set-A F1 0.4348 does not transfer —
   [`CLAIM-LEDGER.md`](CLAIM-LEDGER.md). Low B–D score is the *point* of preregistration: the pipeline is honest enough to fail.

3. **Discovery ≠ grounding.**
   v6 Set-A grounding recall **0.4444** vs v8 discovery exact-match recall **0.0000** (naming contamination from illustrative examples, not empty output) —
   [`results/run_20260730_160338/`](results/run_20260730_160338/),
   [`results/run_20260730_162340/`](results/run_20260730_162340/).
   Concrete misses: [`docs/ERROR_ANALYSIS.md`](docs/ERROR_ANALYSIS.md).

4. **ISA-visibility over-correction fixed (§8, 2026-07-31).**
   The hardened gate rejected the canonical `cache_block_size` parameter because the LLM generated a generic justification without citing a `CBO.*` instruction mnemonic. Fixed by:
   - **Prompt:** added an explicit rule requiring mnemonic citation in `visibility_justification`
   - **Gate:** removed a redundant double-check; `justification_cites_real_mnemonic()` is sufficient
   - **Result:** `cache_block_size` now accepted with `CBO.ZERO`/`CBO.CLEAN` citation. Full-corpus F1 improved from 0.1875 → **0.2353**.

   Details: [`EXPERIMENTS.md` §8](EXPERIMENTS.md#8-over-correction-fix--recover-cache_block_size-2026-07-31).

---

## Results

Every bold number maps to a committed artifact in [`CLAIM-LEDGER.md`](CLAIM-LEDGER.md).
Re-derive offline: `./verify.sh` · slice breakdown:
`python scripts/compute_eval_breakdown.py --results results/run_qwen_fast`

### Current (post-fix §8)

| Slice | P | R | F1 | Notes / source |
|-------|---|---|-----|----------------|
| **Full 30 (post-fix)** ![PRIMARY](https://img.shields.io/badge/-PRIMARY-1F3A5F) | 0.5000 | 0.1538 | **0.2353** | [`run_qwen_fast`](results/run_qwen_fast/) |
| **Set A (post-fix)** | 0.6667 | 0.4444 | **0.5333** | from post-fix run slice |
| **Sets B–D** ![FORWARD--REGISTERED](https://img.shields.io/badge/-FORWARD--REGISTERED-C1710D) | 0.0000 | 0.0000 | 0.0000 | forward-registered eval |
| Hallucination | — | — | **0%** | substring check |

### Previous runs

| Slice | P | R | F1 | Notes / source |
|-------|---|---|-----|----------------|
| Historical Run 5 (archived gold overlay) | 0.3846 | 0.5000 | 0.4348 | pre-unified-gate · [`run_20260717_053803`](results/run_20260717_053803/) + [`archive/pre_r1_fix`](data/gold/archive/pre_r1_fix/) |
| Live full 30 (pre-fix gate) | 0.5000 | 0.1154 | 0.1875 | [`run_20260730_152612`](results/run_20260730_152612/) |
| Live Set A only (pre-fix) | 1.0000 | 0.3333 | 0.5000 | from pre-fix run slice |
| Grounding recall (v6) | — | 0.4444 | — | gold names in prompt · [`run_20260730_160338`](results/run_20260730_160338/) |
| Discovery recall (v8) ![COLD](https://img.shields.io/badge/-COLD-C1710D) | — | 0.0000 | — | zero eval gold names · [`run_20260730_162340`](results/run_20260730_162340/) |
| Variance ΔF1 | — | — | **0.0000** | identical config · [`160338`](results/run_20260730_160338/) vs [`161322`](results/run_20260730_161322/) |

Historical exact vs relaxed (Run 5 only): P 0.3846→0.5000, R 0.5000→0.6000, F1 0.4348→0.5455.

> **⚠️ Falsification triggered:** |0.2353 − 0.4348| > 0.15. Set-A historical F1 does **not** generalize.

### Accepted examples (post-fix §8)

Accepted — [`cache_block_size.yaml`](results/run_qwen_fast/cache_block_size.yaml) (previously rejected, now recovered):

```yaml
- name: cache_block_size
  type: numeric_range
  isa_visible: true
  visibility_justification: CBO.ZERO and CBO.CLEAN operate on cache-block-sized granules,
    so the block size affects the address range of each instruction.
```

Accepted — [`wlrl_field_behavior.yaml`](results/run_qwen_fast/wlrl_field_behavior.yaml):

```yaml
- name: wlrl_supported_values
  type: field_behavior
  isa_visible: true
  visibility_justification: Software can read back the CSR with CSRRS to see which
    written values stick.
```

---

## Challenge deliverable map

| # | Challenge requirement | Proof |
|---|----------------------|-------|
| 1 | LLM details | [Deliverable 1](#deliverable-1--llm-details) · [`config/default.yaml`](config/default.yaml) |
| 2 | Prompt files | [`prompts/`](prompts/) · [`prompts/CHANGELOG.md`](prompts/CHANGELOG.md) |
| 3 | Prompt engineering journey | [`EXPERIMENTS.md`](EXPERIMENTS.md) |
| 4 | Hallucination mitigation | [`src/validate_yaml.py`](src/validate_yaml.py) · [Architecture](#architecture) |
| 5 | Example YAML outputs | [Results](#results) · [`results/run_20260730_152612/`](results/run_20260730_152612/) |
| 6 | Source code | [`src/`](src/) |

---

## Claims NOT being made

Full list: [`CLAIM-LEDGER.md`](CLAIM-LEDGER.md).

| Tempting claim | Reality |
|----------------|---------|
| Historical recall = discovery | Only `v8_discovery` is cold naming |
| Multi-model success | **Not claimed** — only Qwen post-gate artifacts are committed |
| Upstream UDB contribution | Format samples in [`results/udb/`](results/udb/); `cache_block_size` now accepted post-fix — UDB PR viable pending quality review |
| Historical F1 generalizes | Falsified (post-fix 30 F1 = 0.2353; B–D = 0) |

---

## Quick start

```bash
git clone https://github.com/Hiteshsai007/riscv-param-extractor.git
cd riscv-param-extractor
pip install -r requirements.txt

./verify.sh                      # ← before any model step
python -m pytest tests/ -v

# Model-dependent (local Ollama + qwen2.5:7b-instruct)
python -m src.cli --health-check --config config/default.yaml
python -m src.cli --input data/raw_snippets/ --config config/default.yaml
python -m src.eval_harness --results results/<run_dir>/ --gold data/gold/ --snippets data/raw_snippets/
```

Discovery eval (zero gold names): `--config config/discovery.yaml`.

---

## Deliverable 1 — LLM details

| Field | Value |
|-------|-------|
| Model | Qwen 2.5 7B Instruct (`qwen2.5:7b-instruct`) |
| Context | 8,192 tokens |
| Temperature | 0.0 |
| Seed | 42 |
| Runtime | Local Ollama |
| Config | [`config/default.yaml`](config/default.yaml) |

## Deliverable 2 — Prompts & hallucination mitigation

`v1` → `v4` contrastive CoT → **`v6_decision_framework`** (evaluated) → `v8_discovery` (zero gold names).
Log: [`EXPERIMENTS.md`](EXPERIMENTS.md). Evidence must be a **verbatim** source substring
([`src/validate_yaml.py`](src/validate_yaml.py)).

---

## Project structure

<details>
<summary>Expand full tree</summary>

```
riscv-param-extractor/
├── CLAIM-LEDGER.md
├── EXPERIMENTS.md
├── ground_truth.md
├── verify.sh / verify.ps1
├── config/                  # default.yaml, discovery.yaml
├── data/
│   ├── raw_snippets/        # 30 snippets
│   ├── ground_truth/        # R4 preregistration
│   ├── gold/                # grading (+ archive/pre_r1_fix/)
│   ├── eval_sets/set_a/
│   ├── udb_reference/
│   └── riscv_isa_index.json
├── docs/
│   ├── pipeline-architecture.svg
│   └── ERROR_ANALYSIS.md    # concrete misses (B–D / discovery)
├── prompts/                 # v1…v8 + CHANGELOG
├── results/
│   ├── run_20260717_053803/ # historical (pre-gate)
│   ├── run_20260730_152612/ # live unified-gate full 30 (pre-fix)
│   ├── run_qwen_fast/       # post-fix §8 full 30 (current primary)
│   ├── run_20260730_160338/ # Set A variance #1
│   ├── run_20260730_161322/ # Set A variance #2
│   ├── run_20260730_162340/ # discovery (v8)
│   └── udb/                 # format samples — no upstream PR
├── schema/parameter_schema.py
├── scripts/                 # verify.py, check_commit_order.py,
│                             # diagnose_cache_block.py, compute_eval_breakdown.py…
├── src/
└── tests/                   # + tests/bad_examples/
```

</details>

---

## License

Apache License 2.0
