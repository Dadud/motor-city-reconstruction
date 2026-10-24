# Track object index initialization

Native routine `0x42d5b0` walks `0x78`-byte object records. It clears the
three-float delta at `+0x58`. If the animation pointer at `+0x74` is nonzero,
it samples mode 1 at global time zero and writes the resulting position and
3x3 matrix. It then finds the closest track point in XZ, starting at row zero
and checking rows 4, 8, 12, and so on. The selected row is written to `+0x34`
and its arithmetic right shift by three to `+0x38`.

This is not bit-for-bit the same comparison order as helper `0x42d4b0`. The
initial squared distance is stored as binary32, while subsequent x87 candidate
sums stay extended through comparison. Equal points can therefore replace the
initial index when its stored distance rounded upward; repeated equal later
points can continue replacing it. `nearest_track_initialization_point`
preserves that behavior.

`assign_track_object_indices` composes the verified tick-zero animation pose
and the scan over explicit object, animation, and track-table views. 512 direct
calls to the original `0x42d5b0` compare complete object records. Non-float
bytes match exactly; animated position/matrix values use a scale-aware
`max(1e-5, abs(expected)*2e-6)` tolerance. Cases include unanimated and
animated objects, varied track-table sizes, ties, and the initial-distance
rounding behavior. Table construction and global ownership are not covered.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Native comparison: `tools/verify_track_object_indexing.py`.
