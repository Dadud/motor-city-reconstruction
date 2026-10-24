# Normalized shared random fraction

Routine `0x6f2c90` advances the six-word shared random generator at
`0x6f0fa0`, takes the low 16 bits of the returned word, and multiplies by the
exact binary scale `2^-16`. `RandomState.next_unit_fraction` reproduces both
the state transition and the resulting fraction in `[0, 1)`.

1,024 direct calls with supplied initial global states match the returned
binary32 value bit-for-bit. The generator transition itself is independently
compared in `tools/random_state_oracle.py`; this check captures the original
x87 return immediately at the call boundary.

Static provenance: retained Ghidra 12.1.4 pseudocode and direct x86
instruction inspection for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
