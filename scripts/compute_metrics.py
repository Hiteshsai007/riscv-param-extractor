"""Compute metrics for a specific run against gold labels."""

import yaml
from pathlib import Path


def param_key(p):
    return f"{p.get('name','').strip().lower()}::{p.get('type','').strip().lower()}"


def compute(results_dir_name):
    gold_dir = Path("data/gold")
    results_dir = Path(f"results/{results_dir_name}")
    snippets_dir = Path("data/raw_snippets")

    all_extracted = []
    all_gold = []
    yaml_valid = 0
    total_params = 0
    hallucinated = 0

    for subdir in ["positive_cases", "negative_cases"]:
        case_dir = gold_dir / subdir
        for gf in sorted(case_dir.glob("*.yaml")):
            with open(gf) as f:
                gdata = yaml.safe_load(f)
            gold_params = gdata.get("expected_parameters", [])

            result_file = results_dir / f"{gf.stem}.yaml"
            if result_file.exists():
                with open(result_file) as f:
                    rdata = yaml.safe_load(f)
                ext_params = rdata.get("parameters", [])
            else:
                ext_params = []
                print(f"MISSING result: {gf.stem}")

            ext_keys = {param_key(p) for p in ext_params}
            gold_keys = {param_key(p) for p in gold_params}
            tp = ext_keys & gold_keys
            fp = ext_keys - gold_keys
            fn = gold_keys - ext_keys

            # Evidence check
            snippet_file = snippets_dir / f"{gf.stem}.txt"
            source = snippet_file.read_text(encoding="utf-8") if snippet_file.exists() else ""
            for p in ext_params:
                total_params += 1
                ev = p.get("evidence", "")
                if ev in source:
                    yaml_valid += 1
                else:
                    hallucinated += 1
                    print(f"  HALLUC: {gf.stem}/{p.get('name')} - evidence not verbatim")

            status = "OK" if not fp and not fn else ""
            print(f"{gf.stem}: ext={len(ext_params)}, gold={len(gold_params)}, TP={len(tp)}, FP={len(fp)}, FN={len(fn)} {status}")
            if fp:
                print(f"  FP keys: {fp}")
            if fn:
                print(f"  FN keys: {fn}")

            all_extracted.extend(ext_params)
            all_gold.extend(gold_params)

    # Aggregate
    ext_keys = {param_key(p) for p in all_extracted}
    gold_keys = {param_key(p) for p in all_gold}
    tp = ext_keys & gold_keys
    fp = ext_keys - gold_keys
    fn = gold_keys - ext_keys

    tp_c, fp_c, fn_c = len(tp), len(fp), len(fn)
    prec = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0
    rec = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    hall_rate = hallucinated / total_params if total_params > 0 else 0

    print()
    print(f"=== AGGREGATE METRICS ({results_dir_name}) ===")
    print(f"Total extracted: {len(all_extracted)}")
    print(f"Total gold: {len(all_gold)}")
    print(f"TP: {tp_c}, FP: {fp_c}, FN: {fn_c}")
    print(f"Precision: {prec:.4f} ({tp_c}/{tp_c+fp_c})")
    print(f"Recall: {rec:.4f} ({tp_c}/{tp_c+fn_c})")
    print(f"F1: {f1:.4f}")
    print(f"Hallucination: {hall_rate:.4f} ({hallucinated}/{total_params})")
    print(f"Evidence grounded: {yaml_valid}/{total_params}")
    print()
    print(f"TP keys: {sorted(tp)}")
    print(f"FP keys: {sorted(fp)}")
    print(f"FN keys: {sorted(fn)}")


if __name__ == "__main__":
    import sys
    run_name = sys.argv[1] if len(sys.argv) > 1 else "run_20260716_191632"
    compute(run_name)
