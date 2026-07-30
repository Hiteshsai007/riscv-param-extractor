#!/usr/bin/env python3
"""Offline validator for committed extraction results and fixtures."""

import argparse
import sys
from pathlib import Path

import yaml

from src.validate_yaml import validate_yaml_file


def iter_result_files(root: Path):
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.yaml") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate extraction results offline")
    parser.add_argument("path", nargs="?", default="results", help="Path to a results directory or YAML file")
    args = parser.parse_args()

    target = Path(args.path)
    files = []
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = iter_result_files(target)
    else:
        print(f"ERROR: target not found: {target}")
        return 2

    if not files:
        print("No YAML files found")
        return 2

    failures = []
    for yaml_path in files:
        ok, detail = validate_yaml_file(yaml_path)
        if not ok:
            failures.append((yaml_path, detail))

    if failures:
        print("VALIDATION FAILED")
        for path, detail in failures:
            print(f"- {path}: {detail}")
        return 1

    print(f"Validated {len(files)} YAML files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
