# X-axis matrix row rotation

Routine `0x6f1780` rotates rows one and two of a row-major 3×3 matrix by a
turn-based X angle and preserves row zero. It supports in-place operation by
copying its source matrix before writing when input and output alias.

`rotate_matrix_rows_x` implements the row transform and returns a new matrix.
The verifier makes 512 direct original calls with separate buffers and 512
with an aliased input/output buffer. All nine binary32 words match exactly for
both paths, across exact quarter/half turns and randomized finite matrices and
angles. Exceptional float inputs are outside the tested domain.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
