"""Unit test for B2 fix: parser must merge items from MULTIPLE fenced YAML blocks."""
import sys
sys.path.insert(0, '/home/user/riscv-param-extractor')

from src.extract import _parse_yaml_from_response

def test_two_separate_yaml_blocks():
    """Exact reproduction case from the 2026-07-30 failure."""
    raw = '''```yaml
- name: "cache_block_size"
  description: "The size of a cache block."
  type: "numeric_range"
  constraints: null
  evidence: "The capacity and organization of a cache and the size of a cache block are both implementation-specific."
  trigger_keyword: "implementation-specific"
  source_section: "Unprivileged Spec, Cache Management Operations (CMO) §cmo"
  confidence: "high"
  isa_visible: true
  visibility_justification: "Software can query via CBO.ZERO and CBO.CLEAN instructions."
```

```yaml
- name: "cache_capacity_and_organization"
  description: "The capacity and organization of a cache."
  type: "numeric_range"
  constraints: null
  evidence: "The capacity and organization of a cache and the size of a cache block are both implementation-specific."
  trigger_keyword: "implementation-specific"
  source_section: "Unprivileged Spec, Cache Management Operations (CMO) §cmo"
  confidence: "high"
  isa_visible: false
  visibility_justification: "Software can observe/query the cache properties to determine the capacity and organization."
```
'''
    params, rejs = _parse_yaml_from_response(raw)
    names = [p.get("name") for p in params]
    assert "cache_block_size" in names, f"Missing cache_block_size: {names}"
    assert "cache_capacity_and_organization" in names, f"Missing second block param: {names}"
    assert len(params) == 2
    print("✓ test_two_separate_yaml_blocks PASSED — both blocks merged")


def test_single_block_still_works():
    raw = '''```yaml
- name: "test_param"
  description: "test"
  type: "boolean"
  constraints: null
  evidence: "test evidence"
  trigger_keyword: "test"
  source_section: "test"
  confidence: "high"
  isa_visible: true
  visibility_justification: "Software can observe this via CSR."
```
'''
    params, _ = _parse_yaml_from_response(raw)
    assert len(params) == 1
    assert params[0]["name"] == "test_param"
    print("✓ test_single_block_still_works PASSED")


def test_dict_form():
    raw = '''```yaml
parameters:
  - name: "dict_param"
    description: "from dict form"
    type: "numeric_range"
    constraints: null
    evidence: "dict evidence"
    trigger_keyword: "dict"
    source_section: "dict"
    confidence: "high"
    isa_visible: true
    visibility_justification: "Dict form test."
```
'''
    params, _ = _parse_yaml_from_response(raw)
    assert len(params) == 1
    assert params[0]["name"] == "dict_param"
    print("✓ test_dict_form PASSED")


if __name__ == "__main__":
    test_two_separate_yaml_blocks()
    test_single_block_still_works()
    test_dict_form()
    print("\nAll B2 parser tests PASSED")