# Z-axis matrix row rotation

Routine `0x6f1910` rotates rows zero and one of a row-major 3×3 matrix by a
turn-based Z angle and preserves row two. It copies the source matrix before
writing when input and output alias.

`rotate_matrix_rows_z` implements the operation. The verifier makes 512 direct
original calls with separate buffers and 512 with an aliased input/output
buffer. All nine binary32 output words match exactly over quarter/half turns
and randomized finite matrices and angles. Exceptional float inputs remain
outside the tested domain.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
