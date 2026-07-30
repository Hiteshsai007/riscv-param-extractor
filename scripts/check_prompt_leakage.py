#!/usr/bin/env python3
"""
P3.2 — Prompt leakage guard.

Fails if any evaluation-set gold parameter name appears inside prompts/,
except in files or HTML-comment regions clearly marked as off-evaluation
contrastive examples / historical grounding prompts.

Usage:
    python scripts/check_prompt_leakage.py
    python scripts/check_prompt_leakage.py --strict   # also flag grounding prompts
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GOLD_DIRS = [
    ROOT / "data" / "gold" / "positive_cases",
    ROOT / "data" / "gold" / "negative_cases",
]
PROMPTS_DIR = ROOT / "prompts"

# Grounding / historical prompts that intentionally embed gold names (R8).
# Discovery eval must use a prompt NOT in this allowlist.
GROUNDING_PROMPT_ALLOWLIST = {
    "v1_baseline.md",
    "v2_few_shot.md",
    "v3_cot.md",
    "v4_contrastive.md",
    "v5_refined_contrastive.md",
    "v6_decision_framework.md",
    "v7_lfx_hardening.md",
    "CHANGELOG.md",
}

# HTML comments may mark an entire prompt as discovery-safe even if checking
# the body; off-evaluation example blocks use this marker.
OFF_EVAL_MARKER = "off-evaluation"


def load_gold_names() -> set[str]:
    names: set[str] = set()
    for case_dir in GOLD_DIRS:
        if not case_dir.exists():
            continue
        for path in case_dir.glob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for param in data.get("expected_parameters") or []:
                name = param.get("name")
                if name:
                    names.add(name)
            for rej in data.get("rejected_candidates") or []:
                name = rej.get("name")
                if name:
                    names.add(name)
    return names


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def find_leaks(text: str, gold_names: set[str]) -> list[str]:
    found: list[str] = []
    for name in sorted(gold_names):
        # Word-ish match: name as a YAML/string token
        pattern = re.compile(rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])')
        if pattern.search(text):
            found.append(name)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail if prompts leak gold names")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Also fail on grounding prompts (default: allowlist them)",
    )
    args = parser.parse_args()

    gold_names = load_gold_names()
    if not gold_names:
        print("ERROR: no gold names loaded")
        sys.exit(1)

    print(f"Loaded {len(gold_names)} gold parameter names")
    failures: list[str] = []

    for path in sorted(PROMPTS_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        body = strip_html_comments(raw)

        if not args.strict and path.name in GROUNDING_PROMPT_ALLOWLIST:
            leaks = find_leaks(body, gold_names)
            if leaks:
                print(
                    f"[ALLOW grounding] {path.name}: {len(leaks)} gold name(s) "
                    f"(historical / R8 grounding prompt)"
                )
            else:
                print(f"[OK] {path.name}: no gold names")
            continue

        # Discovery / new prompts must be clean
        if OFF_EVAL_MARKER in raw.lower() or path.name.startswith("v8_"):
            leaks = find_leaks(body, gold_names)
        else:
            leaks = find_leaks(body, gold_names)

        if leaks:
            failures.append(f"{path.name}: {', '.join(leaks)}")
            print(f"[FAIL] {path.name}: leaked {leaks}")
        else:
            print(f"[OK] {path.name}: no gold names")

    if failures:
        print(f"\nPROMPT LEAKAGE DETECTED ({len(failures)} file(s)):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print("\nNo unexpected prompt leakage. OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
