# Coarse fixed-angle heading lookup

Routine `0x6f2b90` maps two signed coordinates to an angle in 1/1024-turn
units. It folds the coordinate ratio to one octant, rounds to one of 257 table
entries, then applies quadrant reflection. The recovered table is the original
257-byte sequence at `0x8c8c08`; the 16-bit table used by `0x6f2cc0` is not a
substitute because the quantization differs.

4,096 direct calls match exactly across the axes, all octants, equal-coordinate
diagonals, table-boundary ratios and deterministic random signed coordinates.
`INT_MIN` is excluded: wrapped absolute value participates in signed compares
and produces atypical paths that this implementation does not model.

Static provenance: retained Ghidra pseudocode and direct x86/table inspection
for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
