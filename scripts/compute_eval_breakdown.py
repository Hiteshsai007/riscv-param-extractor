#!/usr/bin/env python3
"""
Compute Set A vs full-corpus metrics, and optional grounding vs discovery recall.

Usage:
  python scripts/compute_eval_breakdown.py --results results/run_XXX/
  python scripts/compute_eval_breakdown.py --results results/run_grounding/ \\
      --discovery-results results/run_discovery/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.eval_harness import evaluate_full, load_gold_labels, compute_precision_recall

SET_A = {
    "cache_block_size",
    "cbo_zero_atomicity",
    "cmo_trigger_behavior",
    "csr_address_encoding",
    "csr_trap_intercept",
    "debug_csr_access",
    "non_coherent_agent_mechanism",
    "warl_field_behavior",
    "wlrl_field_behavior",
    "wpri_field_behavior",
}

# Snippets whose gold parameter names appear in v6_decision_framework.md (R8 grounding)
GROUNDING_SNIPPETS = {
    "cache_block_size",  # cache_block_size name in prompt
    "wlrl_field_behavior",  # wlrl_* names in prompt
    "wpri_field_behavior",  # WPRI negative example (name not a param, but in prompt)
    "csr_trap_intercept",  # csr_access_trap_capability in prompt
    "non_coherent_agent_mechanism",  # non_coherent_agent_cbo_mechanism in prompt
}


def _filter_report_snippets(results_dir: Path, gold_dir: Path, snippets_dir: Path, keep: set[str]):
    """Evaluate only the given snippet stems by staging a filtered view."""
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory(prefix="eval_subset_") as tmp:
        tmp_path = Path(tmp)
        # gold subset
        for sub in ("positive_cases", "negative_cases"):
            src = gold_dir / sub
            dst = tmp_path / "gold" / sub
            dst.mkdir(parents=True, exist_ok=True)
            if not src.exists():
                continue
            for f in src.glob("*.yaml"):
                if f.stem in keep:
                    shutil.copy2(f, dst / f.name)
        # results subset
        rdst = tmp_path / "results"
        rdst.mkdir()
        for f in results_dir.glob("*.yaml"):
            if f.stem in keep or f.name in ("manifest.yaml", "summary.yaml"):
                shutil.copy2(f, rdst / f.name)
        return evaluate_full(str(rdst), str(tmp_path / "gold"), str(snippets_dir))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, help="Primary results dir (usually grounding/v6)")
    parser.add_argument("--discovery-results", help="Optional discovery-prompt results dir")
    parser.add_argument("--gold", default="data/gold")
    parser.add_argument("--snippets", default="data/raw_snippets")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results_dir = Path(args.results)
    gold_dir = Path(args.gold)
    snippets_dir = Path(args.snippets)

    full = evaluate_full(str(results_dir), str(gold_dir), str(snippets_dir))
    set_a = _filter_report_snippets(results_dir, gold_dir, snippets_dir, SET_A)

    # Sets B–D = everything not in Set A that has a result file
    all_gold = set(load_gold_labels(gold_dir).keys())
    forward = all_gold - SET_A
    forward_present = {
        p.stem for p in results_dir.glob("*.yaml")
        if p.stem in forward
    }
    forward_report = (
        _filter_report_snippets(results_dir, gold_dir, snippets_dir, forward_present)
        if forward_present
        else None
    )

    out = {
        "results": str(results_dir),
        "full_corpus": full["aggregate"],
        "full_corpus_relaxed": full["aggregate_relaxed"],
        "set_a": set_a["aggregate"],
        "set_a_relaxed": set_a["aggregate_relaxed"],
        "sets_b_d": forward_report["aggregate"] if forward_report else None,
        "sets_b_d_note": "first evaluation of forward-registered set" if forward_report else None,
    }

    if args.discovery_results:
        disc_dir = Path(args.discovery_results)
        grounding = _filter_report_snippets(
            results_dir, gold_dir, snippets_dir, GROUNDING_SNIPPETS & SET_A
        )
        discovery = _filter_report_snippets(
            disc_dir, gold_dir, snippets_dir, SET_A - GROUNDING_SNIPPETS
        )
        # Also: discovery prompt on grounding snippets (cold) + discovery snippets
        disc_full_set_a = _filter_report_snippets(disc_dir, gold_dir, snippets_dir, SET_A)
        out["grounding_vs_discovery"] = {
            "grounding_prompt": "v6_decision_framework",
            "discovery_prompt": "v8_discovery",
            "grounding_recall_set_a_subset": grounding["aggregate"]["recall"],
            "grounding_precision_set_a_subset": grounding["aggregate"]["precision"],
            "discovery_recall_set_a": disc_full_set_a["aggregate"]["recall"],
            "discovery_precision_set_a": disc_full_set_a["aggregate"]["precision"],
            "discovery_recall_non_grounding_snippets": discovery["aggregate"]["recall"],
            "note": (
                "Grounding column uses v6 results on snippets whose gold names "
                "appear in the prompt. Discovery column uses v8_discovery results "
                "(zero gold names in prompt) on Set A."
            ),
        }

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        def row(label, agg):
            if not agg:
                print(f"  {label}: n/a")
                return
            print(
                f"  {label}: P={agg['precision']:.4f} R={agg['recall']:.4f} "
                f"F1={agg['f1']:.4f} Halluc={agg['hallucination_rate']*100:.1f}% "
                f"(extracted={agg['total_extracted']}, gold={agg['total_gold']})"
            )

        print(f"Results: {results_dir}")
        row("Full corpus (30)", out["full_corpus"])
        row("Set A only (10)", out["set_a"])
        row("Sets B–D (forward-registered)", out["sets_b_d"])
        if "grounding_vs_discovery" in out:
            g = out["grounding_vs_discovery"]
            print("\nGrounding vs Discovery (Set A):")
            print(f"  Grounding recall (v6, name-leaked snippets): {g['grounding_recall_set_a_subset']:.4f}")
            print(f"  Discovery recall (v8, full Set A):           {g['discovery_recall_set_a']:.4f}")
            print(f"  {g['note']}")


if __name__ == "__main__":
    main()
