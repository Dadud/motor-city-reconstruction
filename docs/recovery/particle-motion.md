# Particle motion integration

Routine `0x5273f0` advances the 600-entry particle pool when the signed
half-tick delta from the previous update is positive. It updates two size
channels by the integer tick delta, adds each source definition's Y
acceleration to vertical velocity, and integrates XYZ positions using the
original `1/32` time step. Inactive and source-less records remain untouched.

512 direct calls compare the complete pool and last-update global exactly,
covering positive, zero and negative deltas, active and inactive records,
valid source pointers, and varied finite float fields. Source Y accelerations
are supplied by token; emitter loading and the surrounding frame loop remain
outside this helper translation.

Static provenance: retained Ghidra pseudocode and direct x86 instruction
inspection for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
