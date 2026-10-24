# Track block membership lookup

`0x42d810` checks whether a signed 16-bit block ID occurs in the row selected
by its second argument. Equal query and row arguments return true immediately.
Otherwise, when the global slot count at `0x97dbec` is nonnegative, it scans
slots zero through that count inclusively. IDs begin at `0x97c408 + row*0x6c4
+ 0x190` and advance four bytes per slot.

The retained Ghidra pseudocode expresses the row stride directly. The native
instruction sequence independently derives it: it forms `27*row`, shifts left
four (`432*row`), adds `row`, then scales by four, yielding `0x6c4*row`.
This resolves the apparent stride discrepancy without assuming the decompiler
layout. The signed short load and four-byte increment are visible in the same
body.

`client/track_block_membership.py` exposes the table as an explicit bounded
byte view. `tools/verify_track_block_membership.py` compares the return value
against the pinned original executable for 512 deterministic synthetic cases,
including direct equality, negative global counts, signed IDs, suffix hits,
and misses. This verifies the lookup logic on supplied memory; it does not
recover construction or ownership of the global table.

Static provenance: Ghidra 12.1.4 pseudocode and machine code from the retained
REA export for `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Native comparison: `tools/verify_track_block_membership.py`.
