# Axis-angle rotation matrix

Routine `0x6f1650` builds a row-major 3×3 Rodrigues rotation matrix from a
three-component axis and an angle in turns. It normalizes the axis, uses the
client's turn-based sine/cosine helpers, and returns identity for an exact zero
angle. A zero axis with nonzero angle propagates NaNs through the matrix.

`axis_angle_rotation_matrix` implements those branches. The direct native
comparison covers 512 cases, including principal axes, quarter and half turns,
random finite axes and turns, and zero-axis NaN behavior. Matrix floats match
within `max(3e-7, abs(native)*3e-7)`. Overflow and unusual non-finite input
behavior are outside the supported domain.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
