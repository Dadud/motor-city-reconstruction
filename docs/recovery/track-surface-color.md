# Track-surface vertex color

Routine `0x42e490` returns fixed opaque gray (`0xff7f7f7f`) when its surface
descriptor pointer is null. Otherwise it uses the descriptor's quad index,
loads the four vertex indices from the block's 30-byte quad record, and
averages the low three color bytes independently with integer truncation. The
returned alpha byte is always `0xff`.

`average_surface_vertex_color` expresses the operation over explicit descriptor,
quad, and packed vertex-color data. `tools/verify_track_surface_color.py`
compares 512 randomized direct calls to the original executable and checks the
null-pointer fallback on every case; all 1,024 results match exactly. Unit
tests cover the channel arithmetic, vertex ordering, and fallback. Track block
ownership and renderer use remain outside this function-level check.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
