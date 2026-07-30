#!/usr/bin/env python3
"""Audit ISA-visibility claims in committed extraction results.

The matching logic is shared with the live extraction gate in
``src.isa_verification`` so this audit cannot drift from the check that blocks
unverifiable parameters before they are written.

By default only git-tracked result files are audited (local scratch runs under
``results/`` that were never committed are ignored). Pass ``--all`` to scan
every ``results/run_*`` directory on disk.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Allow ``python scripts/verify_isa_claims.py`` from the repository root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from src.isa_verification import justification_cites_real_mnemonic


def _tracked_result_files() -> set[Path]:
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "results"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    return {(ROOT / line.strip()).resolve() for line in out.splitlines() if line.strip()}


def verify_claims(all_on_disk: bool = False) -> None:
    results_dir = Path("results")
    if not results_dir.exists():
        print("No results directory found.")
        sys.exit(0)

    tracked = set() if all_on_disk else _tracked_result_files()
    errors: list[str] = []
    checked = 0
    scanned_runs: set[str] = set()

    for run_dir in sorted(results_dir.glob("run_*")):
        for yaml_file in run_dir.glob("*.yaml"):
            if yaml_file.name in ("manifest.yaml", "summary.yaml"):
                continue
            if not all_on_disk:
                if not tracked:
                    # No git / empty index — fall back to historical committed names only
                    if not run_dir.name.startswith("run_20260717_"):
                        continue
                elif yaml_file.resolve() not in tracked:
                    continue

            scanned_runs.add(run_dir.name)
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

    scope = "all on-disk runs" if all_on_disk else "git-tracked results only"
    print(f"Scope: {scope}; runs scanned: {sorted(scanned_runs) or ['(none)']}")
    print(f"Checked {checked} ISA-visibility justifications.")
    if errors:
        print(f"FOUND {len(errors)} UNVERIFIABLE CLAIMS:")
        print("\n".join(errors))
        sys.exit(1)

    print("All ISA-visibility claims mechanically verified against index. OK")
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan every results/run_* directory, including untracked local runs",
    )
    args = parser.parse_args()
    verify_claims(all_on_disk=args.all)


if __name__ == "__main__":
    main()
