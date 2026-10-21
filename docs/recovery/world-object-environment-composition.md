# Active-object environment composition

The scheduled `0x4265f0` maintenance callback now has an end-to-end bounded
comparison through its owned `0x520c20` physics step, track environment stage
`0x51e940`, and six-contact force pass `0x51fc00`.

`tools/verify_world_object_maintenance_environment.py` compares 128 complete
`0x4f8` owner records against the hash-verified installed executable. It maps
grid, block, path, and geometry fixtures, runs the original `0x4265f0` →
`0x520c20` → `0x51e940` → `0x51fc00` chain, then compares every byte with the
Python composition. All 128 records match exactly. Each Python run also asserts
that `0x51e940` retained a nonzero surface descriptor, and the native callback
trace confirms correction callbacks `0x43ba40` and `0x43b750` do not run. These
cases establish the normal active-surface path, not the failed-lookup recovery
branch.

`tools/verify_world_object_environment_correction.py` adds 128 complete-owner
comparisons for the failed-lookup branch. The original environment enters
`0x43bfd0`, its original `0x43ba40` search reaches the original `0x43bd30`
empty-mask return, and the reset boundary `0x43b750` is intercepted. In
parallel, the translated search, correction wrapper, and environment stage run
on the same bounded path table; every owner byte matches, including the
`+0x5b4` probe-generation counter and status-dependent vertical-step selection.
The successful geometric response path (`0x51e460`) and full reset integration
remain open.

Separately, `tools/verify_world_object_maintenance_full.py` checks 256 varied
active/inactive maintenance records with `0x51e940` isolated, and
`tools/verify_world_object_environment.py` covers all 2,400 configurations in the
enumerated bounded fixture set across two 1,200-case runs. Those environment
comparisons still control correction children on correction-wrapper fixtures.
Live runtime ownership, correction-chain integration, and coverage beyond the
synthetic mapped fixtures remain open.
