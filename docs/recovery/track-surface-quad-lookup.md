# Track-surface quad lookup

Routine `0x42eed0` requests a spatial leaf for the query point, then visits its
ordered `(block, descriptor)` candidates. Each descriptor selects a 30-byte
quad-index record from the block's quad table. The routine fetches the four
vertices and tests the four XZ edges in order with inclusive `<=` product
comparisons. It returns a pointer to the first matching candidate pair, or
null when the leaf is invalid, empty, or contains no matching quad.

`find_surface_quad_candidate` translates candidate decoding, order, and
containment over explicit decoded block data. The 512-case native comparison
patches only the call to spatial grid lookup `0x552880`, supplying the leaf
pointer. It compares the exact returned candidate-array pointer, including
invalid/empty leaf cases, multiple blocks, descriptor-to-quad indirection,
edge points, interior points, and misses. Thus this validates `0x42eed0` after
candidate generation; the grid-to-leaf selection remains the separate
`0x552880` interface.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Native comparison: `tools/verify_track_surface_quad_lookup.py`.
