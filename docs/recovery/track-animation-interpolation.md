# Track object animation interpolation

`0x407940` samples two adjacent 20-byte animation frames. Its eight-byte
header contains the frame count and interval. Intervals of zero or greater than
400 use 6. Mode 1 wraps the frame index; mode 2 returns zero without writing
outputs once the final interval begins. Mode 1 uses the same frame calculation
and loops over `frame_count - 1` intervals.

The fractional time remains in x87 precision. The previous-frame weight is
stored as binary32 before reuse; the next-frame weight remains extended. Both
multiply the fixed-point signed XYZ frame words. The quaternion shorts are
interpolated with the same weights scaled by 4.0, then `0x553710` expands the
result into a row of nine binary32 matrix values. The scale constant at
`0x83b69c` is the binary32 value nearest `1/65535`.

`evaluate_track_object_animation` and `quaternion_to_matrix` implement these
operations. `tools/verify_track_animation.py` makes 512 randomized native
checks across mode 1, mode 2 before the final interval, mode 2 at the final
interval (including no-write behavior), and standalone quaternion-to-matrix
calls. Position and matrix outputs match within `max(2e-5, abs(expected)*2e-6)`;
the randomized maximum error was below `1e-6`. A second verifier exercised 450
installed type-3 animation payloads over 2,074 mode-1 samples and 450 final
mode-2 checks; its largest output difference was `6.103515625e-5`, one float
step at the largest tested magnitudes.

The recovered caller `0x42d780` now composes this transform and compares its
full object records against 512 original executions. Time is nonnegative and
frame counts are at least two in the implemented domain. Animation allocation,
global ownership, and live renderer scheduling remain outside these checks.

Static provenance: Ghidra 12.1.4 pseudocode and machine code from the retained
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Native comparisons: `tools/verify_track_animation.py`,
`tools/track_object_animation_oracle.py`, and
`tools/verify_animated_track_objects.py`.
