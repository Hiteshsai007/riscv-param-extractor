import yaml
import re

response_text = """```yaml
<thought_process>
Q1: WHO has the choice? The hardware implementation ("implementation-specific"). → Possible parameter.
Q2: Is there genuine variability? Yes — different implementations can have different cache capacities, organization, and block sizes. → Parameter.
Q3: What is the variability axis? The variability is in the size and organization of the cache and block, which can take on multiple values. → type: numeric_range.
Name: cache_capacity_and_block_size
</thought_process>
```yaml
- name: "cache_capacity_and_block_size"
  description: "The capacity and organization of a cache and the size of a cache block are both implementation-specific."
  type: "numeric_range"
  constraints: null
  evidence: "The capacity and organization of a cache and the size of a cache block are both implementation-specific, and the execution environment provides software a means to discover information about the caches and cache blocks in a system."
  trigger_keyword: "implementation-specific"
  source_section: "Unprivileged Spec, Cache Management Operations (CMO) §cmo"
  confidence: "high"
  isa_visible: true
  visibility_justification: "Software can query the cache properties to determine the capacity and organization."
```

```yaml
- name: "cache_block_size_uniformity"
  description: "The size of a cache block is uniform throughout the system."
  type: "boolean"
  constraints: "In the initial set of CMO extensions, the size of a cache block shall be uniform throughout the system."
  evidence: "In the initial set of CMO extensions, the size of a cache block shall be uniform throughout the system."
  trigger_keyword: "uniform"
  source_section: "Unprivileged Spec, Cache Management Operations (CMO) §cmo"
  confidence: "high"
  isa_visible: true
  visibility_justification: "Software can rely on the cache block size being uniform across the system."
"""

cleaned = re.sub(r'<thought_process>.*?</thought_process>', '', response_text, flags=re.DOTALL)
yaml_matches = re.findall(r'```(?:yaml|YAML)?\s*(.*?)\s*(?:```|$)', cleaned, flags=re.DOTALL)
if yaml_matches:
    yaml_text = "\n".join(yaml_matches).strip()
else:
    yaml_text = cleaned.strip()

print("YAML TEXT:")
print(yaml_text)
parsed = yaml.safe_load(yaml_text)
print("PARSED:")
print(parsed)
