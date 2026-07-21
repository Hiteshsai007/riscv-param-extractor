# Spec-Tagging PR Workflow

This document explains how to take the parameters extracted by `riscv-param-extractor` and propose them as official parameter definitions to the [RISC-V Unified Database (UDB)](https://github.com/riscv-software-src/riscv-unified-db).

## 1. Automated Generation

The script `scripts/generate_spec_tags.py` takes a validated extraction YAML file and maps it to the UDB `param_schema.json` format.

**Command:**
```bash
python scripts/generate_spec_tags.py results/run_YOUR_RUN/your_snippet.yaml --outdir results/spec_tag_examples
```

**What it does:**
- Maps the parameter `name` to uppercase UDB naming convention.
- Translates pipeline `type` strings into UDB JSON schema types (e.g., `numeric_range` -> `integer`, `capability` -> `boolean`).
- Copies the extracted `description`.
- Generates a `.yaml` parameter file and a `.patch` diff preview.

## 2. Manual Review & Completion

The generated YAML will contain placeholders that require manual review before submission:

- **`long_name`**: The script title-cases the parameter name. Refine this to match spec terminology.
- **`definedBy`**: This is stubbed with `TODO_EXTENSION_NAME`. You must map the source section (e.g., "Unprivileged Spec, CMO") to the exact UDB extension name (e.g., `Zicbom`).
- **Schema Constraints**: If the extracted parameter has complex constraints (e.g., "Must be a naturally aligned power-of-two"), these may need to be translated into specific JSON schema constraints (`minimum`, `multipleOf`) manually.

## 3. Submitting the PR

1. Fork and clone the `riscv-software-src/riscv-unified-db` repository.
2. Copy your completed `.yaml` file(s) into `spec/std/isa/param/`.
3. Verify against the UDB schema:
   ```bash
   # In the UDB repo
   npm run validate
   ```
4. Commit and push your branch.
5. Open a Pull Request referencing the specific RISC-V specification section where the parameter is defined (which was captured by the extractor's `source_section` output).
