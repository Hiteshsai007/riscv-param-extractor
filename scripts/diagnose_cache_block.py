"""
Diagnostic script: Run the pipeline on cache_block_size.txt and print:
1. The raw LLM response
2. Any ISA-visibility fields in the parsed output
3. The result of justification_cites_real_mnemonic() on any justification text
"""
import sys
import os
import logging
import yaml
from pathlib import Path

os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extract import load_config, _create_client_from_config, _parse_yaml_from_response, enforce_isa_visibility_gate
from src.prompt_manager import get_formatted_prompt
from src.candidate_detector import detect_candidates
from src.isa_verification import justification_cites_real_mnemonic

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def main():
    config = load_config("config/default.yaml")
    client = _create_client_from_config(config)
    
    snippet_path = Path("data/raw_snippets/cache_block_size.txt")
    snippet_text = snippet_path.read_text(encoding="utf-8")
    
    # Strip metadata
    lines = snippet_text.split("\n")
    if lines and lines[0].startswith("# Source:"):
        source_section = lines[0].replace("# Source:", "").strip()
        snippet_text = "\n".join(lines[1:]).strip()
    else:
        source_section = "Unknown"
    
    # Pass 1
    candidates = detect_candidates(snippet_text)
    print(f"\n{'='*80}")
    print(f"PASS 1 CANDIDATES: {len(candidates)}")
    for c in candidates:
        print(f"  [{c.trigger_keyword}] {c.sentence[:100]}...")
    
    # Build prompt
    prompt_version = config.get("prompt", {}).get("version", "v6_decision_framework")
    prompts = get_formatted_prompt(
        version=prompt_version,
        snippet=snippet_text,
        candidates=candidates,
        source_section=source_section,
    )
    
    # Call LLM
    print(f"\n{'='*80}")
    print("CALLING LLM...")
    response = client.chat(
        system_prompt=prompts["system"],
        user_prompt=prompts["user"],
    )
    
    print(f"\n{'='*80}")
    print("RAW LLM RESPONSE:")
    print(f"{'='*80}")
    print(response.content)
    print(f"{'='*80}")
    
    # Parse
    parsed_params, parsed_rejections = _parse_yaml_from_response(response.content)
    
    print(f"\n{'='*80}")
    print(f"PARSED PARAMETERS: {len(parsed_params)}")
    for p in parsed_params:
        print(f"  name: {p.get('name')}")
        print(f"  isa_visible: {p.get('isa_visible')}")
        print(f"  visibility_justification: {p.get('visibility_justification')}")
        
        justification = p.get("visibility_justification", "")
        if justification:
            result = justification_cites_real_mnemonic(justification)
            print(f"  justification_cites_real_mnemonic(): {result}")
        
        # Run the gate
        allowed, reason = enforce_isa_visibility_gate(p)
        print(f"  enforce_isa_visibility_gate(): allowed={allowed}, reason={reason}")
        print()
    
    print(f"\nPARSED REJECTIONS: {len(parsed_rejections)}")
    for r in parsed_rejections:
        print(f"  candidate_text: {r.get('candidate_text', '')[:80]}...")
        print(f"  reason: {r.get('reason')}")
        print(f"  isa_visible: {r.get('isa_visible')}")
        print(f"  visibility_justification: {r.get('visibility_justification')}")
        
        justification = r.get("visibility_justification", "")
        if justification:
            result = justification_cites_real_mnemonic(str(justification))
            print(f"  justification_cites_real_mnemonic(): {result}")
        print()

if __name__ == "__main__":
    main()
