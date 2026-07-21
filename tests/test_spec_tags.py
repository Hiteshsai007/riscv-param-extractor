import os
import subprocess
from pathlib import Path
import yaml

def test_generate_spec_tags(tmp_path):
    """Test the generation of UDB format spec tags."""
    # Create a mock extracted yaml
    input_yaml = tmp_path / "mock_extracted.yaml"
    mock_data = {
        "parameters": [
            {
                "name": "test_param",
                "type": "numeric_range",
                "description": "A test parameter."
            },
            {
                "name": "test_bool",
                "type": "boolean",
                "description": "A boolean param."
            }
        ]
    }
    with open(input_yaml, "w", encoding="utf-8") as f:
        yaml.dump(mock_data, f)
        
    outdir = tmp_path / "out"
    
    # Run the script
    script_path = Path("scripts/generate_spec_tags.py").absolute()
    result = subprocess.run(
        ["python", str(script_path), str(input_yaml), "--outdir", str(outdir)],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert outdir.exists()
    
    # Check outputs
    yaml1 = outdir / "TEST_PARAM.yaml"
    patch1 = outdir / "TEST_PARAM_diff.patch"
    yaml2 = outdir / "TEST_BOOL.yaml"
    
    assert yaml1.exists()
    assert patch1.exists()
    assert yaml2.exists()
    
    # Check content mapping
    with open(yaml1, "r", encoding="utf-8") as f:
        # skip the first '---' line which we add manually in the script
        content = f.read().strip()
        if content.startswith("---"):
            content = content[3:].strip()
        data = yaml.safe_load(content)
        
    assert data["name"] == "TEST_PARAM"
    assert data["schema"]["type"] == "integer"
    assert data["schema"]["minimum"] == 1
    assert "A test parameter" in data["description"]
