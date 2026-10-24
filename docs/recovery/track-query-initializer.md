# Track query record initialization

Native routine `0x42d8d0` writes the selected signed track index to dword 0,
its arithmetic right shift by three to dword 1, and zeroes dwords 2 through 7.
The remaining bytes in the 0x44-byte record are untouched. This helper is now
explicitly represented by `initialize_track_query_state` and used by the
composed track sampler.

The original comparison runs 512 deterministic calls with signed 32-bit
indices and randomized initial records. Every byte of each resulting 0x44-byte
record, including the untouched tail, matches. This validates the initializer
over supplied records; it does not establish the wider live track-query state.

Static provenance: retained Ghidra 12.1.4 pseudocode from the REA export for
`mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Native comparison: `tools/verify_track_query_initializer.py`.
