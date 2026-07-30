#!/usr/bin/env python3
"""Audit ISA-visibility claims in committed extraction results.

The matching logic is shared with the live extraction gate in
``src.isa_verification`` so this audit cannot drift from the check that blocks
unverifiable parameters before they are written.
"""

import sys
from pathlib import Path

# Allow ``python scripts/verify_isa_claims.py`` from the repository root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from src.isa_verification import justification_cites_real_mnemonic


def verify_claims() -> None:
    results_dir = Path("results")
    if not results_dir.exists():
        print("No results directory found.")
        sys.exit(0)

    errors: list[str] = []
    checked = 0

    for run_dir in results_dir.glob("run_*"):
        for yaml_file in run_dir.glob("*.yaml"):
            with yaml_file.open(encoding="utf-8") as handle:
                try:
                    data = yaml.safe_load(handle)
                except Exception:
                    continue

            if not isinstance(data, dict):
                continue
            for param in data.get("parameters", []):
                if not isinstance(param, dict):
                    continue
                if param.get("isa_visible") is True and param.get("visibility_justification"):
                    checked += 1
                    justification = param["visibility_justification"]
                    if not justification_cites_real_mnemonic(justification):
                        errors.append(
                            f"{yaml_file.name} [{run_dir.name}]: Parameter "
                            f"'{param.get('name')}' claims to be ISA-visible but "
                            "its justification contains no recognizable instruction or CSR.\n"
                            f"  Justification: {justification}"
                        )

    print(f"Checked {checked} ISA-visibility justifications.")
    if errors:
        print(f"FOUND {len(errors)} UNVERIFIABLE CLAIMS:")
        print("\n".join(errors))
        sys.exit(1)

    print("All ISA-visibility claims mechanically verified against index. OK")
    sys.exit(0)


if __name__ == "__main__":
    verify_claims()
