# Original collision update and object-pair response

This is a static recovery of the original client's collision path. It extends
the isolated helpers in [collision calculations](calculations/collision-helpers.md)
with their immediate caller order and state layout. It is evidence for the
installed `mcity.exe`, not a portable implementation or a claim that offline
driving now reproduces original collisions.

Source: x86 `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA evidence: dispatcher `0x45abe0`
`ev_1141c7488a98dc1efb2b09ab82f8e4348a36517d1b18c7c8792da6a0a53cb35a`,
terrain/support collision query `0x45a320`
`ev_3ba721e6a5505a901a0ebcb36dd3fb07fd1c6a3946131ac9977cda86a35a1a4a`,
pair response `0x458530`
`ev_68896493e178eddbaf295bf09ebb82c659ee5869655eeaa685680f27756fadac`,
and support correction `0x459150`
`ev_c3f3b262fb8913fa5ff557be4a24aaafac22d2ca4509199dbb425410887d4565`.
Resolved caller inventories: dispatcher `ev_67b289fddb5ac0770da8a2ff488593ee228991de0d9940628d8a2b5a4d5d3437`,
pair response `ev_f3302c55d517f4861df4903eae7227c32095b986500f7d898b17702ef3205eb5`,
terrain query `ev_9693a54e6d7aefe0255cf7962bde769ea9c598834b190cf635a4927765bbf4aa`,
and support correction `ev_261410cd22f78ac888dbb42323b15bb27bc3e9fc796459006450c6118bd9230d`.
Scheduler registration `0x567940` `ev_1c4be5e6e473eb29f29ebd60f1541a78f14d907cd2e5e153acbc3c3dae7c70e8`,
sorted task insertion `0x565d20` `ev_1de03a06f56970d17d820f9ba6336003db14272a9916aaec138b2ccaba3faf93`,
and registration owner `0x5219b0` `ev_1e6b0655b6c0c8910f6e0416fb58d64c5dd9459d7a7ae40e2acd57ebc444871d`.
The original executable and instruction listings remain the authority; the
decompiler pseudocode is provider-specific evidence, not original source.

## Dispatcher order

`0x45abe0` clears the per-object collision record at `+0x3c4` (60 bytes) and
initializes related contact fields before checking the object's active byte at
`+0x4`. Active objects enter the terrain/support state machine:

1. If the contact counter at `+0x3bc` is zero, query `0x45a320`. A failed
   query increments the counter.
2. A speed-like field at `+0x350` is compared with `0.6`. Above that threshold,
   a zero contact counter becomes one. Below it, an existing counter is checked
   by `0x459150`; if that reports support, the speed-like field is cleared,
   an additional high-speed action may run, and `0x45a320` decides whether to
   clear the contact counter.
3. An inactive per-object byte at `+0x7` causes `0x45ce90` to run.
4. When the countdown at `+0x410` is zero and object flags allow collision
   handling, the object enters a global candidate list. Each earlier candidate
   first passes an axis-aligned center-distance test on all three coordinates,
   using the sum of object radii at `+0xd8`.
5. Candidate pairs then call `0x45af30` repeatedly, with at most 33 calls in
   the observed do/while loop. Only a successful sequence proceeds to
   `0x458530`, with a normalized global fallback direction and a shared impact
   record. After candidate processing, the dispatcher calls `0x45cf70` and,
   for objects with flag `0x40`, contact follow-ups through `0x45d1f0`.
6. The active-object tail calls `0x45c3e0` and `0x51e060`.

The ordering above is observed in one function body. The meaning and producers
of several flags, the global candidate-list lifecycle, the 33-attempt policy,
and the side effects in the named callees still need explicit recovery. The
resolved direct-caller inventory is empty because the scheduler stores this
routine as a callback rather than calling it directly. Its actual task execution
and the scheduler's per-frame caller remain open. The dispatcher also has a
fast return when its entry field at `+0x6c` is nonzero.

## Scheduler placement

`0x567940` constructs two task lists. `0x565d20` inserts each callback into a
16-byte record in ascending numeric priority order; the record stores the
priority, callback and owner pointer. In the first list, `0x45abe0` is
registered at priority `0x28` once for every object in each of two global
collections. A separate global callback is also registered at `0x28`. For
context, that list registers vehicle update `0x53c140` at `0x1e` and vehicle
callback `0x43d6e0` at `0x32`; world-object callback `0x5779d0` also runs at
`0x1e`, with global callbacks at `0x1e` and `0x32`. Thus collision dispatch is
placed after those `0x1e` registrations and before `0x32` registrations in this
list. This establishes registration ordering only; it does not prove execution
semantics, frame cadence, task cancellation or how the second list interleaves.
`0x5219b0` calls `0x567940` in a larger game-start routine, but that routine's
state transitions and repeated runtime path have not been recovered here. The
task-list construction is now ported as executable Python in
[game_schedule.py](../client/game_schedule.py), with ordering and capacity
regression cases in `tests/test_game_schedule.py`. It requires explicit object
addresses, flags and allocator observations; original callback addresses remain
opaque IDs until each callback has a portable implementation. The same builder
is ported in C++ in `native/src/scheduler.cpp` and covered by the native scheduler
test, so both source runtimes now construct matching callback lists.

## Terrain query and object pair

`0x45a320` immediately rejects an object with nonzero `+0x6c`; objects with
byte `+0x6` use the specialized `0x54f0e0` path. Other objects select a fixed
triangle-index table by shape value at `+0xdc`: 12 entries for shapes 0 and 2,
6 for shape 1, and 40 for shapes 3 and 4. It checks projected triangle bounds
and signed edge tests, then passes candidate triangle data to helper
`0x6f14f0`. A candidate goes through copied object/contact data and further
projection/height calculations; `0x4b71a0` is the recovered plane-height helper.
The scene/terrain query that supplies these records, exact edge conventions,
and complete output mutation are not yet ported or compared.

`0x458530` constructs world-space sample points from each object's center,
orientation and dimensions. The observed code loops over 32 increments (`i/32`)
and stops early when the relative sample motion is no longer approaching the
supplied radial direction. For each accepted sample it calls `0x458390` to get
the tangential response, writes paired contact records at `+0x3c4` on both
objects (including reciprocal normal/response values and the other-object
pointer), and invokes `0x457780` twice per affected body. Linear deltas are
accumulated into positions; angular deltas are accumulated and scaled by
`1/(2*pi)` into orientation fields. Contact flag `+0x6c` is cleared on each
body that receives response. The routine returns one when its sample loop
records a collision and applies accumulated deltas.

This pair routine depends on the two recovered numerical helpers, but its
sample geometry, iteration order, per-body gating, contact-record layout,
accumulation and coupled body mutations have not yet been reproduced in a
comparison harness. All three oriented-box point-test leaves (`0x45b8e0`,
`0x45bb70`, and `0x45be10`) and the normal selector (`0x45bfe0`) are now
translated to Python and C++; the point tests match 192 direct original calls
each and the selector matches 1,024, as documented. The enclosing pair
routine remains open. `0x459150` likewise transforms an array of support points
and applies terrain-plane corrections, but its complete terrain and contact
producer chain remains open.

## Remaining work

- Recover the data types and producers for collision object shapes, triangles,
  terrain queries, rotations, global candidates and shared contact records.
- Recover and compare `0x45af30`, `0x45cf70`, `0x45d1f0`, `0x45c3e0`, task-list
  execution, and the recurring game-frame caller.
- Port the dispatcher and pair path with ordered callbacks and byte-level
  contact-record checks; then compare controlled original trajectories.
- Integrate it with the force vehicle state and test wall/resting impacts,
  object pairs, terrain contacts, repeated contact persistence and tunnelling.

Until those steps pass, the playable driving mode's prototype collision
behavior and all original collision acceptance gates remain open.

The observed dispatcher order now has a bounded Python source translation in
[`client/collision_dispatch.py`](../client/collision_dispatch.py), documented
with its explicit child and global-state boundaries in
[`collision-dispatch.md`](calculations/collision-dispatch.md). It has focused
unit coverage but no direct original-execution comparison yet; this does not
complete the collision chain above.
