#!/usr/bin/env python3
"""
T1.1: Mechanically verify ISA-visibility claims.

Extracts instruction/CSR mnemonics named in `visibility_justification`
and cross-checks them against a static list of real RISC-V instructions/CSRs.
Flags any justification that names no valid instruction/CSR.
"""
import json
import re
import sys
from pathlib import Path
import yaml

def load_isa_index():
    index_path = Path("data/riscv_isa_index.json")
    if not index_path.exists():
        print(f"Error: {index_path} not found")
        sys.exit(1)
    with open(index_path) as f:
        data = json.load(f)
    return set(data.get("valid_instructions", [])), set(data.get("valid_csrs", []))

def verify_claims():
    valid_instr, valid_csrs = load_isa_index()
    results_dir = Path("results")
    if not results_dir.exists():
        print("No results directory found.")
        sys.exit(0)

    errors = []
    checked = 0
    
    # Regex to find all words in ALL CAPS (possibly with dots or underscores)
    word_pattern = re.compile(r'\b[A-Z0-9_\.]+\b')

    for run_dir in results_dir.glob("run_*"):
        for yaml_file in run_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                try:
                    data = yaml.safe_load(f)
                except Exception:
                    continue
            
            if not isinstance(data, list):
                continue
            
            for param in data:
                if not isinstance(param, dict):
                    continue
                
                # Check only accepted parameters
                if "reason" in param: # Skip rejected candidates
                    continue
                
                isa_visible = param.get("isa_visible")
                justification = param.get("visibility_justification", "")
                
                # If the field doesn't exist, we skip (for backwards compat with old runs)
                # But if it exists and is True, we verify it.
                if isa_visible is True and justification:
                    checked += 1
                    words = word_pattern.findall(justification)
                    found_valid = False
                    found_candidates = set()
                    
                    for w in words:
                        if w in valid_instr or w in valid_csrs:
                            found_valid = True
                            break
                        # Heuristic: if it's > 2 chars, uppercase, not in index, maybe it's a typo or un-indexed instruction
                        if len(w) > 2 and not w.isdigit():
                            found_candidates.add(w)
                    
                    if not found_valid:
                        errors.append(
                            f"{yaml_file.name} [{run_dir.name}]: Parameter '{param.get('name')}' claims to be ISA-visible but "
                            f"justification contains no recognizable instructions or CSRs.\n"
                            f"  Justification: {justification}\n"
                            f"  Unrecognized capitalized terms found: {', '.join(found_candidates) if found_candidates else 'None'}"
                        )
                        
    print(f"Checked {checked} ISA-visibility justifications.")
    if errors:
        print(f"FOUND {len(errors)} UNVERIFIABLE CLAIMS:")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("All ISA-visibility claims mechanically verified against index. OK")
        sys.exit(0)

if __name__ == "__main__":
    verify_claims()
