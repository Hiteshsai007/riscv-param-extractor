# UDB-shaped exports (Hardening Pass 2 / P3.1)

Generated from live unified-gate run `results/run_20260730_152612` via
`scripts/generate_spec_tags.py`, plus a vendored reference shape.

| File | Origin | Upstream PR? |
|------|--------|--------------|
| `WLRL_SUPPORTED_VALUES.yaml` | Live accepted parameter | **No** — already covered by existing UDB concepts; not novel |
| `WLRL_ILLEGAL_WRITE_EXCEPTION.yaml` | Live accepted parameter | **No** — same |
| `SATP_ASID_BITS.yaml` | Live accepted (name differs from UDB `ASID_WIDTH`) | **No** — naming not review-ready vs UDB |
| `CACHE_BLOCK_SIZE_reference_shape.yaml` | Copied from `data/udb_reference/` for schema shape check | **No** — live run extracted **zero** params for `cache_block_size.txt` (both candidates rejected `NOT_ISA_VISIBLE`); do not open an upstream PR

Decision recorded in CLAIM-LEDGER.md.
