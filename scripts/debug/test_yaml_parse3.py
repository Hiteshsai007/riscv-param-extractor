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
lines = cleaned.splitlines()
in_block = False
yaml_lines = []

for line in lines:
    stripped = line.strip()
    if stripped.startswith('```'):
        in_block = not in_block
        continue
    
    if in_block:
        yaml_lines.append(line)
    elif stripped.startswith('- name:'):
        in_block = True
        yaml_lines.append(line)

yaml_text = "\n".join(yaml_lines).strip()
if not yaml_text:
    yaml_text = cleaned.strip()

print("YAML TEXT:")
print(yaml_text)
parsed = yaml.safe_load(yaml_text)
print("PARSED:")
print(parsed)
