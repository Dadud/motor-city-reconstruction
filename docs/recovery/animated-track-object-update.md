# Animated track object update

Routine `0x42d780` walks `0x78`-byte records from global base `0x97c410`, up
to the signed count at `0x97c398`. For each record with a nonzero animation
pointer at `+0x74`, it calls transform routine `0x407940` with mode 1 and the
global time at `0xaa456c`, passing the record's position and its following
matrix. It then stores `(new_position - old_position) * 0x83b7b8` at `+0x58`.
Records without an animation pointer are left untouched.

`update_animated_track_objects` models this caller's record traversal and
delta writes with an explicit position-transform callback. The 512-case
original comparison patches only the call target for `0x407940`, supplying
known positions; all `0x78` bytes across up to seven records are compared.
Thus the loop, gate, argument-independent parent writes, scaling, and untouched
fields are verified. The animation interpolation and matrix transform remain
separate dependencies and are not claimed recovered here.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Original comparison: `tools/verify_animated_track_objects.py`.
