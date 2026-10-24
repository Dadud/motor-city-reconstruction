# 3×3 matrix row scaling

Routine `0x6f1240` scales each of the three rows in a row-major 3×3 float
matrix by the matching X, Y, or Z component of a supplied vector. It writes
nine binary32 outputs to the caller's buffer.

`scale_matrix_rows` implements this operation over explicit matrix and scale
values. The 512-case direct original comparison checks all nine output words
exactly and verifies that the routine does not write beyond the 36-byte result.
Aliasing between the scale vector and output buffer is not part of the tested
domain.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
