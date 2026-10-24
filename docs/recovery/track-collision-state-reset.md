# Track collision state reset

`0x42d2e0` writes `FF 00 00` to each of 1,024 consecutive three-byte metadata
slots at `0x97dbf0`. When the signed global bound `0x97dbec` is nonnegative,
it scans block rows zero through that value, with `0x6c4` row spacing. For a
row with a positive entry count at `+0x69c` and nonnull pointer at `+0x6a0`, it
clears the 16-bit word at pointed-array offset `+2`, then every 24 bytes for
the declared number of entries. It finishes by calling `0x407550`.

`0x407550` resets three dwords in each 24-byte row of the `0x1800`-byte table
at `0x8e3b38`: offsets 0 and 8 become zero, and offset 4 becomes `FFFFFFFF`.
The other 12 bytes of each row remain untouched.

The ports take explicit mutable views for metadata, block rows, pointed arrays,
and the secondary table. 256 direct native calls to `0x42d2e0` compare every
byte of these regions; the same batch includes 256 independent direct calls to
`0x407550` and compares its entire table. Cases include negative bounds,
empty/nonempty rows, null pointers, nonpositive counts, and sparse pointed
arrays. These checks establish the reset behavior over supplied memory; they do
not establish allocation or ownership of the globals.

Static provenance: retained Ghidra 12.1.4 pseudocode and native bodies from the
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Native comparison: `tools/verify_track_collision_state.py`.
