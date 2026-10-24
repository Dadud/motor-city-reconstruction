# 3×3 matrix product

Routine `0x6f2a60` computes a row-major 3×3 matrix product and supports output
aliasing either input. When both input pointers are the same output buffer, it
computes the in-place square. Its multiply/add order is preserved by
`multiply_3x3`.

The 512-case native comparison executes four arrangements per case: disjoint
output, output equal to the left input, output equal to the right input, and
all pointers equal. All nine binary32 outputs match the original bit-for-bit
across 2,048 calls, and a guard after each output confirms the 36-byte write
boundary. Partial overlap and exceptional float inputs are outside scope.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
