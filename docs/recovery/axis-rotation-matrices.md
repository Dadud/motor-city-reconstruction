# Axis rotation matrices

Routines `0x6f1530`, `0x6f1590`, and `0x6f15f0` build row-major 3×3 X-, Y-,
and Z-axis rotation matrices from an angle measured in turns. They share the
client's turn-to-radian sine/cosine helpers. Python exposes the builders as
`rotation_x_turns`, `rotation_y_turns`, and `rotation_z_turns`.

`tools.verify_axis_rotation_matrices.py` compares 512 original executions per
entry, including exact quarter-turn cases and randomized positive and negative
turns. All 1,536 matrices matched within absolute float tolerance `2e-7`.
Exceptional inputs and the caller's matrix-composition order are outside these
constructor-level checks.

Static provenance: retained Ghidra 12.1.4 pseudocode and native bodies from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
