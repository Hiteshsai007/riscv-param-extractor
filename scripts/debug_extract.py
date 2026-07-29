"""
Phase 0 diagnostic: Run extraction on cache_block_size.txt with full visibility
into every pipeline stage.
"""
import logging
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.extract import extract_from_snippet, enforce_isa_visibility_gate
from pathlib import Path
import yaml

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

with open("config/default.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

snippet_path = Path("data/raw_snippets/cache_block_size.txt")
with open(snippet_path, "r", encoding="utf-8") as f:
    snippet_text = f.read()

source_section = "Unprivileged Spec, Cache Management Operations (CMO) §cmo"

print("=" * 70)
print("PHASE 0 DIAGNOSTIC: cache_block_size.txt")
print("=" * 70)

result = extract_from_snippet(
    snippet_text=snippet_text,
    source_section=source_section,
    source_file=snippet_path.name,
    config=config
)

print("\n" + "=" * 70)
print(f"EXTRACTION SUMMARY: {result.parameters_extracted} validated, "
      f"{len(result.rejected_candidates)} rejections, "
      f"{len(result.hallucination_flags)} hallucination flags")
print("=" * 70)

print("\n--- VALIDATED PARAMETERS ---")
for i, p in enumerate(result.parameters):
    print(f"\n  [{i+1}] name: {p.name}")
    print(f"      type: {p.type}")
    print(f"      isa_visible: {p.isa_visible}")
    print(f"      visibility_justification: {p.visibility_justification}")
    print(f"      evidence (first 80 chars): {p.evidence[:80]}...")
    print(f"      confidence: {p.confidence}")

print("\n--- REJECTED CANDIDATES ---")
for i, r in enumerate(result.rejected_candidates):
    print(f"\n  [{i+1}] candidate_text: {r.candidate_text[:80]}...")
    print(f"      reason: {r.reason}")

print("\n--- HALLUCINATION FLAGS ---")
for flag in result.hallucination_flags:
    print(f"  {flag}")

if not result.hallucination_flags:
    print("  (none)")

print("\n--- R1 ACCEPTANCE CHECK ---")
names_extracted = [p.name for p in result.parameters]
rejected_reasons = {getattr(r, 'candidate_text', ''): getattr(r, 'reason', '') for r in result.rejected_candidates}

has_cache_block_size = 'cache_block_size' in names_extracted
has_bad_param = any('cache_capacity_and_organization' in n for n in names_extracted)

print(f"  cache_block_size extracted: {has_cache_block_size}")
print(f"  cache_capacity_and_organization in extracted: {has_bad_param}")
print(f"  All extracted names: {names_extracted}")
print(f"  Rejected reasons: {rejected_reasons}")

if has_cache_block_size and not has_bad_param:
    print("\n  ✓ R1 PASS: cache_block_size accepted, cache_capacity_and_organization not present")
else:
    print("\n  ✗ R1 PARTIAL: see details above")
