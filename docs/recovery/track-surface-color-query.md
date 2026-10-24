# Track-surface color query

Routine `0x42e590` calls `0x42eed0` to find a containing surface candidate. If
none is found it returns `0xffffffff`. For a hit, it resolves the candidate's
block and descriptor, follows the descriptor's quad index, loads four packed
vertex colors and averages their low RGB channels independently, returning
opaque alpha.

`surface_color_from_candidate` expresses the post-lookup behavior over explicit
block data and composes with `average_surface_vertex_color`. The 512-case
original comparison supplies the candidate at the `0x42eed0` call boundary,
then compares exact packed return words for a hit and the no-hit sentinel on
every case. This verifies the color-query logic after candidate selection;
spatial leaf generation and candidate traversal remain separately bounded.

Static provenance: retained Ghidra 12.1.4 pseudocode and native body from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
