import os
from pathlib import Path

def test_udb_reference_data_exists():
    """Verify that the UDB reference data was successfully fetched."""
    udb_dir = Path("data/udb_reference")
    
    # Check if the directory and provenance file exist
    assert udb_dir.exists(), "UDB reference directory missing. Run scripts/fetch_udb_reference.py"
    assert (udb_dir / "provenance.yaml").exists(), "provenance.yaml missing"
    
    # Check that at least one param file is downloaded
    yaml_files = list(udb_dir.glob("*.yaml"))
    # Should have at least provenance.yaml + CACHE_BLOCK_SIZE.yaml
    assert len(yaml_files) >= 2 
