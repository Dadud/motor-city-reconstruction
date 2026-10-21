# World-object array update adapter

The recovered array callback at `0x426730` walks active rows at `0x4f8`-byte
strides and invokes `0x520250` on each owner. The math and field writes for
`0x520250` are implemented in `client/world_object_update.py`; the byte-image
adapter in `client/world_object_record.py` now connects them to the original
owner layout, and `update_object_array` applies the callback in array order.

The adapter reads the object identifier at `+0x00`, active byte at `+0x04`,
position at `+0x08`, linear velocity at `+0x14`, angular velocity at `+0x38`,
center of mass at `+0x5c`, rotation at `+0x78`, local vertices at `+0xe0`, and
projection basis at `+0x328`. It writes the integrated position, rotation,
transpose, projected values and 22 transformed points at `+0x1e8`. Other bytes
are retained. This closes the data-layout gap between the previously
independently callable translation and the original active-object array pass.

`tools/verify_world_object_update.py` checks one complete resulting `0x4f8`
byte image against the installed executable, including untouched bytes.
`tools/verify_world_object_array.py` then runs the original `0x426730` array
dispatcher with its live `0x520250` child and compares complete bytes for four
active/inactive row patterns. Task-list execution, full environment/contact
scheduling, collision dispatch and the complete game frame remain separate
recovery gates.

The adjacent `0x4265f0` maintenance pass now has a record adapter too:
`maintain_object_record` calls a required mutable-record `0x520c20` physics
callback for active rows, then applies the observed damping, angular-speed cap
and settling nudge to that same row. The original comparison isolates only
`0x520c20` and checks the full owner image across all six maintenance branches;
it does not establish the environment/contact behavior of the child.
