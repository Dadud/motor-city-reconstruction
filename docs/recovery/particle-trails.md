# Particle trail aging

Routine `0x527360` visits 200 trail records in a selected group. For each
active record it reads the pointed-to definition, increments one of 26 type
counters for IDs 1 through 25, computes the progress byte using wrapped
signed-int multiplication and truncating signed division, then decrements the
remaining count. A zero progress byte expires the record immediately.

512 direct calls compare all record bytes and all 26 counters exactly, across
random active/inactive records, supported definition IDs, durations and byte
weights. Definition data and the selected group are supplied; initialization
and rendering of the trail pool remain outside this function translation.

Static provenance: retained Ghidra pseudocode and direct x86 instruction
inspection for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
