# Fixed-step vector sequence

`client.matrix_math.linear_vector_sequence` translates `mcity.exe` function
`0x4954c0`. The routine copies its two supplied 3D seed points, computes the
binary32 delta from the first to the second, then repeatedly adds that delta to
the prior point. This preserves the native repeated-addition rounding rather
than calculating each point as `first + n * delta`.

`tools/vector_sequence_oracle.py` compares every produced float for 512
deterministic cases against the installed x86 executable. Counts range from
two through 64 and seed components vary over ±1,000,000; all outputs matched
bit-for-bit. Static caller resolution returned no direct callers, so the
function's runtime use remains unknown. This is an isolated helper recovery,
not evidence for a larger track subsystem.

Evidence: `ev_837e11cc3b483c45e48314e1273a6733cda614a50a02b2f441c453a80c4732cb`,
Ghidra 12.1.4 on `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
