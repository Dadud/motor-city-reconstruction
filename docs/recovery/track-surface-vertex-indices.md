# Track-surface vertex indices

Routine `0x42e3f0` accepts a two-word `(block, descriptor)` reference, reads
the descriptor's quad index at offset `+6`, loads its 30-byte quad record, and
writes four pointers to the block's vertex array. The Python helper
`surface_quad_vertex_indices` exposes the equivalent four indices over explicit
descriptor and quad tables.

`tools.verify_surface_quad_vertex_indices.py` compares all four returned native
pointers against 512 randomized direct calls, including nonzero block offsets,
descriptor-to-quad indirection, and varied quad tables. Every pointer matched
exactly. Block lifetime and callers' later vertex interpretation are outside
this helper-level check.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
