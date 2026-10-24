# Cached track-surface quad query

The first branch of `0x42e760` accepts a cached quad when context word
`+0x0c` is nonzero and the query XZ point lies inside all four oriented edges.
On a hit it copies the original three float words into context words 8–10 and
returns `1` without entering the broader world lookup.

`client/track_surface_query.py::cached_quad_hit` translates this hit decision
and payload. Five hundred twelve direct original calls match the return value
and the complete 0x44-byte query record for varied quad geometry and interior
points. The cache-miss world search remains outside this subregion.
