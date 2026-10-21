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
`0x43bfd0`; its original `0x43ba40` search reaches `0x43bd30`'s empty-mask
return, and the original `0x43b750` reset runs through final dispatch. Its
`0x53d640` geometry/reset child is replaced with the translated implementation.
The Python search, correction wrapper, and full translated reset run on the
same bounded inputs and match every owner byte, including the `+0x5b4`
probe-generation counter and path-wrap reset transitions. Successful surface
response (`0x51e460`) has a separate 24-case composition in
`tools/verify_collision_recovery_response.py`: the original `0x43bd30`,
`0x42e010`, and `0x51e460` execute on a valid surface hit, while translated
search/geometry/contact-frame code matches the complete owner image (maximum
compared float error `1.4013e-45`). This covers one bounded collision-mask and
surface fixture; broader dynamic geometry, owner/traffic interaction, and live
service effects remain open.

Separately, `tools/verify_world_object_maintenance_full.py` checks 256 varied
active/inactive maintenance records with `0x51e940` isolated, and
`tools/verify_world_object_environment.py` covers all 2,400 configurations in the
enumerated bounded fixture set across two 1,200-case runs. Those environment
comparisons still control correction children on correction-wrapper fixtures.
Live runtime ownership, correction-chain integration, and coverage beyond the
synthetic mapped fixtures remain open.
