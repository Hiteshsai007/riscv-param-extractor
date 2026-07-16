"""
CLI Entry Point — Main interface for the RISC-V parameter extraction pipeline.

Usage:
    # Run on a single snippet
    python -m src.cli --input data/raw_snippets/cache_block.txt --config config/default.yaml

    # Run on all snippets in a directory
    python -m src.cli --input data/raw_snippets/ --config config/default.yaml

    # Run with a specific model config
    python -m src.cli --input data/raw_snippets/ --config config/models/qwen2_5.yaml

    # Health check (verify LLM endpoint is reachable)
    python -m src.cli --health-check --config config/default.yaml
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.extract import (
    create_run_manifest,
    extract_from_snippet,
    load_config,
    _create_client_from_config,
)
from src.llm_client import LLMClient


def _setup_logging(config: dict[str, Any]) -> None:
    """Configure logging from config."""
    log_level = config.get("logging", {}).get("level", "INFO")
    log_file = config.get("logging", {}).get("log_file")

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def _resolve_input_files(input_path: str) -> list[Path]:
    """Resolve input path to a list of snippet files."""
    path = Path(input_path)

    if path.is_file():
        return [path]
    elif path.is_dir():
        files = sorted(path.glob("*.txt"))
        if not files:
            logging.error("No .txt files found in %s", path)
            sys.exit(1)
        return files
    else:
        logging.error("Input path not found: %s", path)
        sys.exit(1)


def _extract_section_from_file(snippet_path: Path) -> str:
    """
    Try to extract source_section from snippet file metadata.

    Convention: first line of snippet file may contain a metadata comment:
    # Section: Privileged Spec §2.1

    If not present, uses the filename as section identifier.
    """
    with open(snippet_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()

    if first_line.startswith("# Section:"):
        return first_line.replace("# Section:", "").strip()
    elif first_line.startswith("# Source:"):
        return first_line.replace("# Source:", "").strip()

    return snippet_path.stem.replace("_", " ").title()


def run_extraction(args: argparse.Namespace) -> None:
    """Run the extraction pipeline on input files."""
    config = load_config(args.config)
    _setup_logging(config)
    logger = logging.getLogger(__name__)

    # Resolve input files
    input_files = _resolve_input_files(args.input)
    logger.info("Processing %d input file(s)", len(input_files))

    # Create output directory
    output_dir = Path(
        config.get("pipeline", {}).get("output_dir", "results/")
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Create LLM client (reuse across snippets)
    client = _create_client_from_config(config)

    # Write run manifest
    manifest = create_run_manifest(
        config=config,
        input_files=[str(f) for f in input_files],
        output_dir=str(run_dir),
    )
    manifest_path = run_dir / "manifest.yaml"
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
    logger.info("Run manifest written to %s", manifest_path)

    # Process each snippet
    all_results = []
    for snippet_path in input_files:
        logger.info("Processing: %s", snippet_path.name)

        snippet_text = snippet_path.read_text(encoding="utf-8")

        # Strip metadata comment line if present
        lines = snippet_text.split("\n")
        if lines and (lines[0].startswith("# Section:") or lines[0].startswith("# Source:")):
            source_section = lines[0].replace("# Section:", "").replace("# Source:", "").strip()
            snippet_text = "\n".join(lines[1:]).strip()
        else:
            source_section = snippet_path.stem.replace("_", " ").title()

        result = extract_from_snippet(
            snippet_text=snippet_text,
            source_section=source_section,
            source_file=str(snippet_path),
            config=config,
            client=client,
        )

        # Save individual result
        result_path = run_dir / f"{snippet_path.stem}.yaml"
        with open(result_path, "w", encoding="utf-8") as f:
            yaml.dump(
                result.model_dump(mode="json"),
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        all_results.append(result)
        logger.info(
            "  → %d candidates, %d parameters extracted, %d hallucination flags",
            result.candidates_found,
            result.parameters_extracted,
            len(result.hallucination_flags),
        )

    # Write summary
    summary = {
        "run_id": run_id,
        "total_snippets": len(all_results),
        "total_candidates": sum(r.candidates_found for r in all_results),
        "total_parameters": sum(r.parameters_extracted for r in all_results),
        "total_hallucination_flags": sum(
            len(r.hallucination_flags) for r in all_results
        ),
        "snippets": [
            {
                "file": r.source_file,
                "candidates": r.candidates_found,
                "parameters": r.parameters_extracted,
                "hallucinations": len(r.hallucination_flags),
            }
            for r in all_results
        ],
    }

    summary_path = run_dir / "summary.yaml"
    with open(summary_path, "w", encoding="utf-8") as f:
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False)

    logger.info("=" * 60)
    logger.info("Run complete: %s", run_dir)
    logger.info(
        "Total: %d snippets, %d parameters extracted",
        len(all_results),
        sum(r.parameters_extracted for r in all_results),
    )


def run_health_check(args: argparse.Namespace) -> None:
    """Verify LLM endpoint is reachable and model is available."""
    config = load_config(args.config)
    _setup_logging(config)
    logger = logging.getLogger(__name__)

    client = _create_client_from_config(config)

    model_name = config.get("model", {}).get("name", "unknown")
    provider = config.get("model", {}).get("provider", "unknown")

    logger.info("Checking %s at %s...", model_name, provider)

    if client.health_check():
        logger.info("[OK] LLM endpoint is healthy. Model '%s' is available.", model_name)
    else:
        logger.error("[FAIL] LLM endpoint check failed. Is %s running?", provider)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RISC-V Architectural Parameter Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli --input data/raw_snippets/cache_block.txt --config config/default.yaml
  python -m src.cli --input data/raw_snippets/ --config config/default.yaml
  python -m src.cli --health-check --config config/default.yaml
        """,
    )
    parser.add_argument(
        "--input",
        help="Path to a snippet file or directory of snippet files (.txt)",
    )
    parser.add_argument(
        "--config",
        default="config/default.yaml",
        help="Path to pipeline configuration file (default: config/default.yaml)",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Check if the LLM endpoint is reachable and exit",
    )

    args = parser.parse_args()

    if args.health_check:
        run_health_check(args)
    elif args.input:
        run_extraction(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
