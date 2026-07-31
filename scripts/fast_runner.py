import argparse
import concurrent.futures
import datetime
import logging
from pathlib import Path
import yaml
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.extract import extract_from_snippet, load_config, _create_client_from_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def process_snippet(snippet_path, config):
    try:
        client = _create_client_from_config(config)
        with open(snippet_path, "r", encoding="utf-8") as f:
            snippet_text = f.read()
            
        source_section = "Unknown"
        first_line = snippet_text.splitlines()[0] if snippet_text else ""
        if first_line.startswith("# Source:"):
            source_section = first_line.replace("# Source:", "").strip()
            snippet_text = "\n".join(snippet_text.split("\n")[1:]).strip()
            
        result = extract_from_snippet(
            snippet_text=snippet_text, 
            source_section=source_section, 
            source_file=snippet_path.name, 
            config=config,
            client=client
        )
        return snippet_path, result, None
    except Exception as e:
        return snippet_path, None, e

def main():
    config = load_config("config/default.yaml")
    snippets_dir = Path("data/raw_snippets")
    out_dir = Path(f"results/run_qwen_fast")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    snippet_files = list(snippets_dir.glob("*.txt"))
    
    manifest = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "config": config,
        "processed_files": [],
        "failed_files": []
    }
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_snippet, p, config): p for p in snippet_files}
        for future in concurrent.futures.as_completed(futures):
            path, result, err = future.result()
            if err:
                logging.error(f"Failed {path.name}: {err}")
                manifest["failed_files"].append(path.name)
            else:
                out_path = out_dir / f"{path.stem}.yaml"
                with open(out_path, "w", encoding="utf-8") as f:
                    yaml.dump(result.model_dump(mode="json"), f, sort_keys=False)
                manifest["processed_files"].append(path.name)
                logging.info(f"Done {path.name}")
                
    with open(out_dir / "manifest.yaml", "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False)

if __name__ == "__main__":
    main()
