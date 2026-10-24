# Three-vector cross product

Routine `0x6f3b75` writes the ordinary three-component cross product of two
float vectors to a caller-provided output buffer. Its result is not normalized;
the normalized helper `0x6f10d0` composes this primitive with `0x6f1100`.

`cross_product3` reproduces the three binary32 output words. The direct native
comparison covers 512 finite vector pairs, including basis vectors and mixed
sign inputs, and every output word matches exactly. Overflow and exceptional
input behavior are outside this finite-vector check.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
