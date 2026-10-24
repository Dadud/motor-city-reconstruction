# Track-row side status

Routines `0x42e0a0` and `0x42e160` use the selected `0x54`-byte track row.
They subtract the row origin at `+0x00` from the supplied XYZ point, storing
the three deltas as binary32, then take an x87 dot product with the row normal
at `+0x24`. A strictly positive result selects status byte `+0x51`; zero or a
negative result selects `+0x50`.

`track_row_side_status` returns the selected byte, matching `0x42e0a0`.
`track_row_has_type_two` checks that same byte for value 2, matching
`0x42e160`. 512 direct original calls to each function match their low-byte
returns across random rows and points, including exact zero distance and
points offset along either normal direction.

The track row and selected index are explicit bounded inputs. The functions'
live global pointer ownership and row construction are not covered here.

Static provenance: retained Ghidra pseudocode and native bodies from the REA
export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Native comparison: `tools/verify_track_row_side_status.py`.
