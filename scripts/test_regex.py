import re
s = """```yaml
<thought>
</thought>
```yaml
- name: foo
```"""
print(re.findall(r'```(?:yaml|YAML)?\s*(.*?)\s*```', s, re.DOTALL))
