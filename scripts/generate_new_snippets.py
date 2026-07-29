import os
import yaml

snippets = [
    {
        "name": "pmp_granularity",
        "section": "Privileged Spec, PMP",
        "text": "# Source: Privileged Spec, PMP\nThe PMP granularity (G) is implementation-specific, but must be a power of two greater than or equal to 4 bytes.",
        "params": [{
            "name": "pmp_granularity",
            "type": "numeric_range",
            "isa_visible": True,
            "visibility_justification": "Software writes to PMPCFG and PMPADDR CSRs and can observe the granularity by checking which bits stick.",
            "rationale": "PMP granularity dictates the minimum region size software can protect."
        }],
        "rejections": []
    },
    {
        "name": "asid_width",
        "section": "Privileged Spec, SATP",
        "text": "# Source: Privileged Spec, SATP\nThe number of ASID bits implemented in SATP is implementation-defined, up to a maximum of 16 bits.",
        "params": [{
            "name": "asid_width",
            "type": "numeric_range",
            "isa_visible": True,
            "visibility_justification": "Software can determine the ASID width by writing all ones to the ASID field of SATP and reading back the value.",
            "rationale": "The number of supported ASID bits is a classic implementation-defined hardware parameter."
        }],
        "rejections": []
    },
    {
        "name": "vlen_size",
        "section": "Vector Extension Spec",
        "text": "# Source: Vector Extension Spec\nThe vector length VLEN is an implementation-specific power of two, representing the number of bits in a single vector register.",
        "params": [{
            "name": "vlen_size",
            "type": "numeric_range",
            "isa_visible": True,
            "visibility_justification": "Software can discover VLEN by executing a vector configuration instruction (VSETVLI) and reading the resulting vector length.",
            "rationale": "VLEN dictates the fundamental size of vector state."
        }],
        "rejections": []
    },
    {
        "name": "elen_size",
        "section": "Vector Extension Spec",
        "text": "# Source: Vector Extension Spec\nThe maximum element length ELEN is an implementation-specific power of two.",
        "params": [{
            "name": "elen_size",
            "type": "numeric_range",
            "isa_visible": True,
            "visibility_justification": "Software can attempt to configure elements up to ELEN using VSETVLI; unsupported element widths will trap or be rejected.",
            "rationale": "ELEN limits the datatypes that can be processed."
        }],
        "rejections": []
    },
    {
        "name": "pte_a_d_update_mechanism",
        "section": "Privileged Spec, Virtual Memory",
        "text": "# Source: Privileged Spec, Virtual Memory\nThe mechanism for updating PTE A and D bits is implementation-specific. Implementations may choose to update them in hardware or trap to software.",
        "params": [{
            "name": "pte_a_d_update_mechanism",
            "type": "enumerated",
            "isa_visible": True,
            "visibility_justification": "Software can observe whether a store instruction (e.g. SC.W) to an unaccessed page completes successfully (hardware update) or raises a page fault exception.",
            "rationale": "This fundamentally alters OS page table management flow."
        }],
        "rejections": []
    },
    {
        "name": "stval_illegal_inst_behavior",
        "section": "Privileged Spec, Exceptions",
        "text": "# Source: Privileged Spec, Exceptions\nWhen an illegal instruction exception occurs, implementations may optionally set stval to the instruction that caused the trap.",
        "params": [{
            "name": "stval_illegal_inst_behavior",
            "type": "boolean",
            "isa_visible": True,
            "visibility_justification": "Software trap handlers read the STVAL CSR to determine if the faulting instruction was provided.",
            "rationale": "Implementation choice on whether to provide debug info."
        }],
        "rejections": []
    },
    {
        "name": "nmi_cause_update",
        "section": "Privileged Spec, Interrupts",
        "text": "# Source: Privileged Spec, Interrupts\nWhether mcause is updated on a Non-Maskable Interrupt (NMI) is implementation-defined.",
        "params": [{
            "name": "nmi_cause_update",
            "type": "boolean",
            "isa_visible": True,
            "visibility_justification": "Software NMI handlers read MCAUSE to determine the source, and will see either the NMI code or the previous exception code.",
            "rationale": "Affects state visible in NMI handler."
        }],
        "rejections": []
    },
    {
        "name": "misa_writability",
        "section": "Privileged Spec, MISA",
        "text": "# Source: Privileged Spec, MISA\nWhether the misa CSR is writable is implementation-specific. If writable, software can enable or disable extensions dynamically.",
        "params": [{
            "name": "misa_writability",
            "type": "boolean",
            "isa_visible": True,
            "visibility_justification": "Software can attempt a CSRRW instruction to MISA and observe if the value changes.",
            "rationale": "Dynamic extension configuration is a major capability."
        }],
        "rejections": []
    },
    {
        "name": "mvendorid_value",
        "section": "Privileged Spec, Machine IDs",
        "text": "# Source: Privileged Spec, Machine IDs\nThe mvendorid CSR contains a JEDEC manufacturer ID, which is implementation-specific. If not implemented, it returns zero.",
        "params": [{
            "name": "mvendorid_value",
            "type": "numeric_range",
            "isa_visible": True,
            "visibility_justification": "Software reads the MVENDORID CSR directly.",
            "rationale": "Standard ID register."
        }],
        "rejections": []
    },
    {
        "name": "marchid_value",
        "section": "Privileged Spec, Machine IDs",
        "text": "# Source: Privileged Spec, Machine IDs\nThe marchid CSR contains a microarchitecture ID, which is implementation-specific.",
        "params": [{
            "name": "marchid_value",
            "type": "numeric_range",
            "isa_visible": True,
            "visibility_justification": "Software reads the MARCHID CSR directly.",
            "rationale": "Standard ID register."
        }],
        "rejections": []
    },
    {
        "name": "mimpid_value",
        "section": "Privileged Spec, Machine IDs",
        "text": "# Source: Privileged Spec, Machine IDs\nThe mimpid CSR contains an implementation ID, reflecting the version of the microarchitecture.",
        "params": [{
            "name": "mimpid_value",
            "type": "numeric_range",
            "isa_visible": True,
            "visibility_justification": "Software reads the MIMPID CSR directly.",
            "rationale": "Standard ID register."
        }],
        "rejections": []
    },
    {
        "name": "mconfigptr_presence",
        "section": "Privileged Spec, Configuration",
        "text": "# Source: Privileged Spec, Configuration\nThe mconfigptr CSR may optionally be implemented to provide a pointer to a configuration data structure.",
        "params": [{
            "name": "mconfigptr_presence",
            "type": "boolean",
            "isa_visible": True,
            "visibility_justification": "Software can read the MCONFIGPTR CSR; if unimplemented, it raises an illegal instruction exception.",
            "rationale": "Presence of a structural CSR."
        }],
        "rejections": []
    },
    {
        "name": "hpmcounter_width",
        "section": "Privileged Spec, Performance Counters",
        "text": "# Source: Privileged Spec, Performance Counters\nThe width of the hardware performance counters is implementation-defined, up to 64 bits.",
        "params": [{
            "name": "hpmcounter_width",
            "type": "numeric_range",
            "isa_visible": True,
            "visibility_justification": "Software can write all-ones to a performance counter CSR and read it back to determine its width.",
            "rationale": "Counter width affects profiling tools."
        }],
        "rejections": []
    },
    {
        "name": "mmu_tlb_size",
        "section": "Privileged Spec, TLB",
        "text": "# Source: Privileged Spec, TLB\nThe size and associativity of the Translation Lookaside Buffer (TLB) are implementation-specific details that do not affect the execution semantics of instructions.",
        "params": [],
        "rejections": [{
            "text": "The size and associativity of the Translation Lookaside Buffer (TLB)",
            "reason": "NOT_ISA_VISIBLE",
            "isa_visible": False,
            "visibility_justification": "TLB size is a microarchitectural detail that affects performance, but does not alter the functional behavior of any RISC-V instruction like SFENCE.VMA or memory loads.",
            "rationale": "Microarchitectural detail."
        }]
    },
    {
        "name": "branch_predictor_type",
        "section": "Privileged Spec, Branch Predictor",
        "text": "# Source: Privileged Spec, Branch Predictor\nThe type of branch predictor used is implementation-specific. Software should not rely on any particular branch prediction algorithm.",
        "params": [],
        "rejections": [{
            "text": "The type of branch predictor",
            "reason": "NOT_ISA_VISIBLE",
            "isa_visible": False,
            "visibility_justification": "Branch predictors affect execution speed but cannot be directly observed via ISA instructions.",
            "rationale": "Classic microarchitectural detail."
        }]
    }
]

import os

os.makedirs('data/raw_snippets', exist_ok=True)
os.makedirs('data/ground_truth', exist_ok=True)

# Write snippets and ground truth YAML
for s in snippets:
    # write snippet
    snippet_file = f"data/raw_snippets/{s['name']}.txt"
    with open(snippet_file, 'w') as f:
        f.write(s['text'])
    
    # write ground truth
    gt_file = f"data/ground_truth/{s['name']}.yaml"
    gt_data = {
        "snippet_file": snippet_file,
        "source_section": s['section'],
        "expected_parameters": [],
        "expected_rejections": []
    }
    
    for p in s['params']:
        gt_data["expected_parameters"].append({
            "name": p["name"],
            "type": p["type"],
            "isa_visible": p["isa_visible"],
            "visibility_justification": p["visibility_justification"],
            "rationale": p["rationale"]
        })
        
    for r in s["rejections"]:
        gt_data["expected_rejections"].append({
            "candidate_text": r["text"],
            "reason": r["reason"],
            "isa_visible": r["isa_visible"],
            "visibility_justification": r["visibility_justification"],
            "rationale": r["rationale"]
        })
        
    with open(gt_file, 'w') as f:
        yaml.dump(gt_data, f, sort_keys=False)

# Update ground_truth.md
with open('ground_truth.md', 'w') as f:
    f.write("# Ground Truth Ledger (R4)\n\nThis file indexes the precommitted ground truth annotations for the LFX evaluation corpus.\n\n")
    f.write("## Annotated Snippets\n\n")
    
    # List original 10
    originals = [
        "cache_block_size", "cbo_zero_atomicity", "cmo_trigger_behavior",
        "csr_address_encoding", "csr_trap_intercept", "debug_csr_access",
        "non_coherent_agent_mechanism", "warl_field_behavior",
        "wlrl_field_behavior", "wpri_field_behavior"
    ]
    for i, orig in enumerate(originals, 1):
        f.write(f"{i}. **{orig}**\n")
        
    # List new 15
    for i, new_s in enumerate(snippets, len(originals) + 1):
        f.write(f"{i}. **{new_s['name']}**\n")
