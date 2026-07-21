# UDB Reference Data

This directory contains parameter definitions downloaded directly from the 
[RISC-V Unified Database (UDB)](https://github.com/riscv-software-src/riscv-unified-db).

These files serve as the ground-truth formatting and schema reference for 
how architectural parameters are encoded in the RISC-V ecosystem.

## Structure
- `*.yaml`: Individual parameter definitions in UDB format.
- `provenance.yaml`: Metadata on when and from what commit these files were fetched.

Use `scripts/fetch_udb_reference.py` to update this directory.
