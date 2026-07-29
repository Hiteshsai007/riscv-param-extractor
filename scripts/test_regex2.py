import re

s = """```yaml
<thought_process>
Q1: WHO has the choice? Software (OS) has the choice of updating A and D bits, or hardware can do it. Wait, the spec says "implementations may choose to update them in hardware or trap to software". The hardware implementation chooses whether to support hardware A/D bit updates. -> Possible parameter.
Q2: Is there genuine variability? Yes, some implementations do it in hardware, some trap. -> Parameter.
Q3: What is the variability axis? It's a mechanism choice: hardware update vs software trap. -> type: enumerated.
Name: pte_a_d_update_mechanism
</thought_process>
```yaml
[]
```"""

c = re.sub(r'<thought_process>.*?</thought_process>', '', s, flags=re.DOTALL)
print("c:")
print(repr(c))

j = re.sub(r'```(?:yaml|YAML)?|```|\s+', '', c)
print("j:")
print(repr(j))
