\### POSITIVE: Cache block size (ISA-visible)



\*\*CRITICAL RULE (must obey):\*\*  

For any cache-block-size candidate you \*\*MUST\*\* cite one of these \*\*exact\*\* mnemonics in the justification:  

`CBO.ZERO`, `CBO.CLEAN`, `CBO.FLUSH`, or `CBO.INVAL`.  

Never use "CMO", "CMO instructions", or any other spelling.



Example of a \*\*correct\*\* justification:

```yaml

\- name: "cache\_block\_size"

&#x20; type: "numeric\_range"

&#x20; isa\_visible: true

&#x20; visibility\_justification: "CBO.ZERO and CBO.CLEAN operate on cache-block-sized granules, so the block size affects the address range of each instruction."

