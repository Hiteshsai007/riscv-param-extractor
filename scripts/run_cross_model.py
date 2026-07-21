#!/usr/bin/env python3
"""
Run cross-model extraction and generate a disagreement report (FR1).
"""
import argparse
import datetime
import json
import logging
from pathlib import Path

import yaml

# Import existing pipeline components
from src.extract import extract_from_snippet

from src.eval_harness import generate_disagreement_report

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def merge_configs(default_path: str, model_path: str) -> dict:
    """Merge the default config with the model-specific overrides."""
    with open(default_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    with open(model_path, "r", encoding="utf-8") as f:
        model_config = yaml.safe_load(f)
        
    config.update(model_config)
    return config

def main():
    parser = argparse.ArgumentParser(description="Run cross-model evaluation.")
    parser.add_argument("--model-a-config", default="config/default.yaml", help="Config for Model A (Qwen)")
    parser.add_argument("--model-b-config", default="config/models/llama3_1.yaml", help="Config for Model B (Llama)")
    parser.add_argument("--snippets-dir", default="data/raw_snippets", help="Directory of snippets")
    parser.add_argument("--gold-dir", default="data/gold", help="Directory of gold labels")
    parser.add_argument("--results-dir-a", default=None, help="If provided, skips running Model A and uses this results dir")
    args = parser.parse_args()

    snippets_dir = Path(args.snippets_dir)
    gold_dir = Path(args.gold_dir)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir_b = Path(f"results/run_llama_{timestamp}")
    out_dir_b.mkdir(parents=True, exist_ok=True)
    
    config_a = yaml.safe_load(open(args.model_a_config, "r", encoding="utf-8"))
    
    if args.results_dir_a:
        out_dir_a = Path(args.results_dir_a)
        logging.info(f"Skipping Model A execution, using existing results from {out_dir_a}")
        models_to_run = [
            (merge_configs("config/default.yaml", args.model_b_config), out_dir_b, "Model B (Llama)")
        ]
    else:
        out_dir_a = Path(f"results/run_qwen_{timestamp}")
        out_dir_a.mkdir(parents=True, exist_ok=True)
        models_to_run = [
            (config_a, out_dir_a, "Model A (Qwen)"),
            (merge_configs("config/default.yaml", args.model_b_config), out_dir_b, "Model B (Llama)")
        ]
    
    for config, out_dir, desc in models_to_run:
        logging.info(f"Starting {desc} - {config['model']['name']}")
        snippet_files = list(snippets_dir.glob("*.txt"))
        
        manifest = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "config": config,
            "processed_files": [],
            "failed_files": []
        }
        
        for snippet_path in snippet_files:
            logging.info(f"Processing {snippet_path.name}...")
            with open(snippet_path, "r", encoding="utf-8") as f:
                snippet_text = f.read()
                
            try:
                # Same fixed determinism logic in extract_from_snippet
                source_section = "Unknown"
                first_line = snippet_text.splitlines()[0] if snippet_text else ""
                if first_line.startswith("# Source:"):
                    source_section = first_line.replace("# Source:", "").strip()
                
                result = extract_from_snippet(
                    snippet_text=snippet_text, 
                    source_section=source_section, 
                    source_file=snippet_path.name, 
                    config=config
                )
                
                # result is an ExtractionResult object, we need to dictify it for yaml
                out_path = out_dir / f"{snippet_path.stem}.yaml"
                with open(out_path, "w", encoding="utf-8") as f:
                    yaml.dump(result.model_dump(mode="json"), f, sort_keys=False)
                manifest["processed_files"].append(snippet_path.name)
            except Exception as e:
                logging.error(f"Failed {snippet_path.name}: {e}")
                manifest["failed_files"].append(snippet_path.name)
                
        with open(out_dir / "manifest.yaml", "w", encoding="utf-8") as f:
            yaml.dump(manifest, f, sort_keys=False)

    # 2. Generate disagreement report
    logging.info("Generating disagreement report...")
    report = generate_disagreement_report(
        results_dir_a=out_dir_a,
        results_dir_b=out_dir_b,
        gold_dir=gold_dir,
        snippets_dir=snippets_dir,
        model_a_name="Qwen-2.5",
        model_b_name="Llama-3.1"
    )
    
    report_path = Path("results") / f"cross_model_report_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    logging.info(f"Cross-model report saved to {report_path}")
    logging.info("Run complete. See EXPERIMENTS.md for how to analyze this report.")

if __name__ == "__main__":
    main()
