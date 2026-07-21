#!/usr/bin/env python3
"""
Fetch UDB parameter files to ground the gold dataset.
"""
import argparse
import datetime
import json
import logging
from pathlib import Path

import requests
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Files to download from UDB
UDB_FILES = [
    "CACHE_BLOCK_SIZE.yaml",
    "FORCE_UPGRADE_CBO_INVAL_TO_FLUSH.yaml",
    "MUTABLE_MISA_A.yaml",
    "MISALIGNED_LDST.yaml",
    "NUM_PMP_ENTRIES.yaml",
    "ASID_WIDTH.yaml",
    "M_MODE_ENDIANNESS.yaml",
    "ELEN.yaml",
    "PMLEN.yaml",
    "MXLEN.yaml"
]

def main():
    parser = argparse.ArgumentParser(description="Fetch UDB reference files.")
    parser.add_argument("--commit", default="main", help="Git commit SHA to fetch from")
    parser.add_argument("--outdir", default="data/udb_reference", help="Output directory")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    base_url = f"https://raw.githubusercontent.com/riscv-software-src/riscv-unified-db/{args.commit}/spec/std/isa/param"
    
    provenance = {
        "commit": args.commit,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": {}
    }

    for file_name in UDB_FILES:
        url = f"{base_url}/{file_name}"
        logging.info(f"Downloading {url}")
        
        resp = requests.get(url)
        if resp.status_code == 200:
            content = resp.text
            
            # Save the file
            file_path = outdir / file_name
            file_path.write_text(content, encoding="utf-8")
            
            provenance["files"][file_name] = url
        else:
            logging.error(f"Failed to download {file_name}: {resp.status_code}")

    # Save provenance
    prov_path = outdir / "provenance.yaml"
    with open(prov_path, "w", encoding="utf-8") as f:
        yaml.dump(provenance, f, sort_keys=False)

    logging.info(f"Finished downloading {len(provenance['files'])} files to {outdir}")

if __name__ == "__main__":
    main()
