# Animated track object update

Routine `0x42d780` walks `0x78`-byte records from global base `0x97c410`, up
to the signed count at `0x97c398`. For each record with a nonzero animation
pointer at `+0x74`, it calls transform routine `0x407940` with mode 1 and the
global time at `0xaa456c`, passing the record's position and its following
matrix. It then stores `(new_position - old_position) * 0x83b7b8` at `+0x58`.
Records without an animation pointer are left untouched.

`update_animated_track_objects` models the caller's record traversal and delta
writes. `update_animated_track_objects_from_tracks` composes it with the
recovered mode-1 `0x407940` keyframe sampler. In 512 uninterrupted calls to the
original `0x42d780`, with real `0x407940` and `0x553710` instructions executing,
all non-float object bytes match exactly; changed position, matrix, and delta
fields match within `max(1e-5, abs(expected)*2e-6)`. Cases include empty and
multi-object arrays, null and nonnull animation pointers, varied times, signed
fixed-point keyframes, and signed quaternion components.

This composition covers the supplied table and animation records. It does not
establish how the game constructs or owns those globals, nor the full live
renderer lifecycle.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Original comparison: `tools/verify_animated_track_objects.py`.
