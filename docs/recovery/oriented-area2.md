# Rounded 2D oriented area

Routine `0x6f2da0` computes the signed 2D cross product
`(B.x-A.x)*(C.y-A.y) - (C.x-A.x)*(B.y-A.y)`. The x87 result is spilled to
binary32 before it is converted to signed int32 using the active nearest-even
rounding mode. `rounded_oriented_area2` models the binary32 input coordinates,
the determinant spill and the integer result for finite in-range values.

512 direct original calls match exactly, covering both signs, half-integer
rounding and deterministic randomized coordinates. Nonfinite values and
determinants outside signed int32 range are outside the normal-return domain.

Static provenance: retained Ghidra 12.1.4 pseudocode and direct x86 instruction
inspection for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
