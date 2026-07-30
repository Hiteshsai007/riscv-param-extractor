#!/usr/bin/env python3
"""
R6 — Zero-Call Reproducibility Verification Script.

Re-derives published metrics from committed raw outputs and verifies they match
the numbers reported in README.md / CLAIM-LEDGER.md.

Requires NO API key, no model call, no network — pure re-derivation from
committed data. Runs in seconds. Exits non-zero on any mismatch.

Usage:
    python scripts/verify.py           # Verify all claims
    python scripts/verify.py --list    # Show which claims are checkable
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.eval_harness import evaluate_full, load_gold_labels


# ---------------------------------------------------------------------------
# Historical Run 5 (pre-R1 gold for cache_block_size)
# ---------------------------------------------------------------------------
HISTORICAL_RESULTS = Path("results/run_20260717_053803")
HISTORICAL_GOLD_ARCHIVE = Path(
    "data/gold/archive/pre_r1_fix/cache_block_size.yaml"
)
HISTORICAL_EXPECTED = {
    "precision_strict": 0.3846,
    "recall_strict": 0.5000,
    "f1_strict": 0.4348,
    "hallucination_rate": 0.0,  # percent
}

# Live unified-gate run — Hardening Pass 2 primary corpus evaluation.
LIVE_RESULTS: Path | None = Path("results/run_20260730_152612")
LIVE_EXPECTED = {
    "precision_strict": 0.5000,
    "recall_strict": 0.1154,
    "f1_strict": 0.1875,
    "hallucination_rate": 0.0,  # percent
}

CHECKABLE_CLAIMS = {
    "precision_strict": {
        "description": "Strict precision (historical Run 5 vs pre-R1 archived gold)",
        "report_path": ("aggregate", "precision"),
        "source": "Evaluation Metrics table / CLAIM-LEDGER historical row",
    },
    "recall_strict": {
        "description": "Strict recall (historical Run 5 vs pre-R1 archived gold)",
        "report_path": ("aggregate", "recall"),
        "source": "Evaluation Metrics table / CLAIM-LEDGER historical row",
    },
    "f1_strict": {
        "description": "Strict F1 (historical Run 5 vs pre-R1 archived gold)",
        "report_path": ("aggregate", "f1"),
        "source": "Evaluation Metrics table / CLAIM-LEDGER historical row",
    },
    "hallucination_rate": {
        "description": "Hallucination rate (historical Run 5)",
        "report_path": ("aggregate", "hallucination_rate"),
        "source": "Evaluation Metrics table",
        "transform": lambda x: x * 100,  # README reports as percentage
    },
}

NOT_CHECKABLE = [
    "Relaxed precision/recall/F1 — reported in README but requires re-running "
    "the relaxed matcher. This IS checkable via evaluate_full() but not yet "
    "wired into the verification table.",
    "Llama 3.1 8B metrics — all marked N/A (Failed) because the run never completed.",
    "Grounding vs discovery recall split — requires the discovery-prompt live run "
    "artifacts and per-snippet recall decomposition (P1.1).",
    "Run-to-run variance — requires two identical-config committed runs (P1.2).",
]


def resolve_report_value(report: dict, path: tuple) -> float:
    """Navigate nested dict by path tuple."""
    current: Any = report
    for key in path:
        current = current[key]
    return current


def _materialize_historical_gold(dest: Path) -> None:
    """
    Build a temporary gold tree identical to live gold, except cache_block_size
    is replaced by the pre-R1 archived revision used to grade Run 5.
    """
    live_gold = Path("data/gold")
    for subdir in ("positive_cases", "negative_cases"):
        src_dir = live_gold / subdir
        dst_dir = dest / subdir
        dst_dir.mkdir(parents=True, exist_ok=True)
        if not src_dir.exists():
            continue
        for yaml_file in src_dir.glob("*.yaml"):
            target = dst_dir / yaml_file.name
            if yaml_file.stem == "cache_block_size" and subdir == "positive_cases":
                target.write_text(
                    HISTORICAL_GOLD_ARCHIVE.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            else:
                target.write_text(yaml_file.read_text(encoding="utf-8"), encoding="utf-8")


def evaluate_historical() -> dict[str, Any]:
    """Re-derive Run 5 metrics against archived pre-R1 gold."""
    if not HISTORICAL_RESULTS.exists():
        raise FileNotFoundError(f"Historical results missing: {HISTORICAL_RESULTS}")
    if not HISTORICAL_GOLD_ARCHIVE.exists():
        raise FileNotFoundError(
            f"Archived pre-R1 gold missing: {HISTORICAL_GOLD_ARCHIVE}"
        )

    with tempfile.TemporaryDirectory(prefix="gold_historical_") as tmp:
        gold_dir = Path(tmp)
        _materialize_historical_gold(gold_dir)
        return evaluate_full(
            str(HISTORICAL_RESULTS),
            str(gold_dir),
            "data/raw_snippets",
        )


def extract_live_reported_metrics(readme_path: Path) -> dict[str, float | None]:
    """Extract full-corpus live metrics from README Live Unified Gate table if present."""
    content = readme_path.read_text(encoding="utf-8")
    live_section = re.search(
        r"## (?:Results \(live unified gate\)|Evaluation Metrics \(Live Unified Gate.*?\))."
        r"*(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    if not live_section:
        return {k: None for k in LIVE_EXPECTED}

    region = live_section.group(1)
    # Prefer the Full corpus row: | Full corpus (30) | P | R | F1 | Halluc |
    row = re.search(
        r"Full corpus \(30\)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)%",
        region,
    )
    if not row:
        return {k: None for k in LIVE_EXPECTED}
    return {
        "precision_strict": float(row.group(1)),
        "recall_strict": float(row.group(2)),
        "f1_strict": float(row.group(3)),
        "hallucination_rate": float(row.group(4)),
    }


def _print_claim_table(
    title: str,
    report: dict[str, Any],
    expected: dict[str, float],
) -> list[str]:
    print(f"\n{title}")
    print(f"{'Claim':<25} {'Computed':>10} {'Expected':>10} {'Status':>8}")
    print("-" * 60)

    mismatches: list[str] = []
    for claim_id, claim in CHECKABLE_CLAIMS.items():
        computed_raw = resolve_report_value(report, claim["report_path"])
        transform = claim.get("transform")
        computed = transform(computed_raw) if transform else computed_raw
        expected_val = expected[claim_id]

        if abs(computed - expected_val) > 0.01:
            status = "FAIL"
            mismatches.append(
                f"  {claim_id}: computed={computed:.4f}, expected={expected_val:.4f}"
            )
        else:
            status = "OK"
        print(f"{claim_id:<25} {computed:>10.4f} {expected_val:>10.4f} {status:>8}")

    return mismatches


def do_verify() -> None:
    """Main verification logic."""
    readme_path = Path("README.md")
    if not readme_path.exists():
        print("ERROR: README.md not found.")
        sys.exit(1)

    print("Re-deriving metrics from committed results (zero API calls)...")

    # --- Historical Run 5 vs archived pre-R1 gold ---
    try:
        historical_report = evaluate_historical()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    mismatches = _print_claim_table(
        "Historical Run 5 (pre-R1 archived gold)",
        historical_report,
        HISTORICAL_EXPECTED,
    )

    # --- Corrected-gold delta on the same historical artifacts (informational) ---
    corrected_on_historical = evaluate_full(
        str(HISTORICAL_RESULTS),
        "data/gold",
        "data/raw_snippets",
    )
    h = historical_report["aggregate"]
    c = corrected_on_historical["aggregate"]
    print("\nGold-correction delta on historical Run 5 artifacts (informational):")
    print(
        f"  F1 {h['f1']:.4f} (pre-R1 gold) -> {c['f1']:.4f} (corrected gold); "
        f"R {h['recall']:.4f} -> {c['recall']:.4f}; "
        f"P {h['precision']:.4f} -> {c['precision']:.4f}"
    )
    print(
        "  (Denominator change: cache_capacity_and_organization removed from "
        "expected_parameters; TP set unchanged for this run.)"
    )

    # --- Live unified-gate run (only when explicitly configured or README has Live table) ---
    live_results = LIVE_RESULTS
    readme_text = readme_path.read_text(encoding="utf-8")
    has_live_readme_table = bool(
        re.search(
            r"## (?:Results \(live unified gate\)|Evaluation Metrics \(Live Unified Gate)",
            readme_text,
        )
    )

    if live_results is None and has_live_readme_table:
        live_results = _discover_live_results(tracked_only=True)

    if live_results is not None and live_results.exists():
        print(f"\nLive unified-gate run: {live_results}")
        live_report = evaluate_full(
            str(live_results),
            "data/gold",
            "data/raw_snippets",
        )
        reported = extract_live_reported_metrics(readme_path)
        live_expected = {
            k: reported[k] if reported.get(k) is not None else LIVE_EXPECTED[k]
            for k in LIVE_EXPECTED
        }
        mismatches.extend(
            _print_claim_table(
                "Live Unified Gate full corpus (current gold)",
                live_report,
                live_expected,
            )
        )
    else:
        print(
            "\nLive unified-gate run: not yet committed "
            "(set LIVE_RESULTS in scripts/verify.py after P0.2)."
        )

    # Sanity: live gold must not expect the R1-forbidden parameter
    live_labels = load_gold_labels("data/gold")
    cbs = live_labels.get("cache_block_size", {})
    expected_names = {p.get("name") for p in cbs.get("expected_parameters", [])}
    if "cache_capacity_and_organization" in expected_names:
        mismatches.append(
            "  gold_isa_visibility: cache_capacity_and_organization still in "
            "expected_parameters (contradicts R1 / NOT_ISA_VISIBLE)"
        )
        print("\n[FAIL] Live gold still expects cache_capacity_and_organization")
    else:
        print(
            "\n[OK] Live gold: cache_capacity_and_organization not in "
            "expected_parameters"
        )

    if mismatches:
        print(f"\nMISMATCHES FOUND ({len(mismatches)}):")
        for m in mismatches:
            print(m)
        sys.exit(1)

    print("\nAll checkable claims match re-derived values. OK")
    sys.exit(0)


def _discover_live_results(tracked_only: bool = True) -> Path | None:
    """Find a results dir whose YAMLs contain isa_visible (optionally git-tracked only)."""
    results_root = Path("results")
    if not results_root.exists():
        return None

    tracked: set[str] = set()
    if tracked_only:
        try:
            import subprocess

            out = subprocess.check_output(
                ["git", "ls-files", "results"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                parts = Path(line).parts
                if len(parts) >= 2:
                    tracked.add(parts[1])  # results/<run_id>/...
        except (subprocess.CalledProcessError, FileNotFoundError):
            tracked = set()

    candidates: list[Path] = []
    for run_dir in sorted(results_root.glob("run_*")):
        if run_dir.name.startswith("run_20260717_"):
            continue  # historical, pre-gate fields
        if tracked_only and tracked and run_dir.name not in tracked:
            continue
        has_isa = False
        for yml in run_dir.glob("*.yaml"):
            if yml.name in ("manifest.yaml", "summary.yaml"):
                continue
            text = yml.read_text(encoding="utf-8", errors="ignore")
            if "isa_visible" in text:
                has_isa = True
                break
        if has_isa:
            candidates.append(run_dir)

    return candidates[-1] if candidates else None


def do_list() -> None:
    """Show which claims are checkable and which are not."""
    print("=== CHECKABLE CLAIMS ===")
    print("These are verified by re-deriving from committed artifacts:\n")
    for claim_id, claim in CHECKABLE_CLAIMS.items():
        print(f"  [{claim_id}] {claim['description']}")
        print(f"    Source: {claim['source']}")
        print()
    print("  Historical gold overlay:")
    print(f"    {HISTORICAL_GOLD_ARCHIVE}")
    print(f"  Historical results: {HISTORICAL_RESULTS}")
    print()

    print("=== NOT CHECKABLE (honestly labeled) ===")
    print("These claims are NOT verified by this script:\n")
    for note in NOT_CHECKABLE:
        print(f"  • {note}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify all published metrics match committed artifacts (R6)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Show which claims are checkable and which are not",
    )
    args = parser.parse_args()

    if args.list:
        do_list()
    else:
        do_verify()


if __name__ == "__main__":
    main()
