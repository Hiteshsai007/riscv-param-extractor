#!/usr/bin/env python3
"""
Generate UDB-format parameter YAML files from extracted pipeline outputs.
Serves as a PR preview for integrating parameters into the RISC-V UDB.
"""
import argparse
import sys
from pathlib import Path

import yaml

def generate_udb_param(extracted_param: dict) -> dict:
    """
    Map an extracted parameter dictionary to the UDB parameter schema format.
    """
    param_name = extracted_param.get("name", "").upper()
    
    # Map types to JSON schema types used in UDB
    p_type = extracted_param.get("type", "")
    schema_type = "string"
    
    if p_type == "numeric_range":
        schema_type = "integer"
    elif p_type in ("boolean", "capability"):
        schema_type = "boolean"
        
    description = extracted_param.get("description", "")
    if description and not description.endswith("\n"):
        description += "\n"
        
    long_name = param_name.replace("_", " ").title()

    udb_dict = {
        "$schema": "param_schema.json#",
        "kind": "parameter",
        "name": param_name,
        "description": description,
        "long_name": long_name,
        "schema": {
            "type": schema_type
        }
    }
    
    if schema_type == "integer":
        udb_dict["schema"]["minimum"] = 1 # Reasonable default for sizes

    # Placeholder for definedBy since it requires manual mapping
    udb_dict["definedBy"] = {
        "extension": {
            "name": "TODO_EXTENSION_NAME"
        }
    }
    
    return udb_dict

def main():
    parser = argparse.ArgumentParser(description="Generate UDB spec tags from extracted parameters.")
    parser.add_argument("input_yaml", help="Path to a validated extraction YAML file")
    parser.add_argument("--outdir", default="results/spec_tag_examples", help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.input_yaml)
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        sys.exit(1)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    params = data.get("parameters", [])
    if not params:
        print(f"No parameters found in {input_path}.")
        sys.exit(0)

    for p in params:
        udb_format = generate_udb_param(p)
        param_name_upper = udb_format["name"]
        
        out_path = outdir / f"{param_name_upper}.yaml"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("---\n\n")
            yaml.dump(udb_format, f, sort_keys=False)
            
        print(f"Generated {out_path}")
        
        # Generate a mock patch file
        patch_path = outdir / f"{param_name_upper}_diff.patch"
        patch_content = f"""--- /dev/null
+++ b/spec/std/isa/param/{param_name_upper}.yaml
@@ -0,0 +1,15 @@
+---
+
+# yaml-language-server: $schema=../../../schemas/param_schema.json
+
+$schema: param_schema.json#
+kind: parameter
+name: {param_name_upper}
+description: |
+  {udb_format['description'].strip()}
+long_name: {udb_format['long_name']}
+schema:
+  type: {udb_format['schema']['type']}
+definedBy:
+  extension:
+    name: TODO_EXTENSION_NAME
"""
        with open(patch_path, "w", encoding="utf-8") as f:
            f.write(patch_content)
        print(f"Generated {patch_path}")

if __name__ == "__main__":
    main()
