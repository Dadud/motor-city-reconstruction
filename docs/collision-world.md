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

`0x458530` constructs center-of-mass contact levers and radial directions from
the supplied world-space point. It samples for up to 32 steps and stops when
relative point motion ceases to approach the supplied normal. Each accepted
step calls `0x458390` for tangential response and `0x457780` for normal and
tangential body response. The step fraction scales the applied impulses, while
point velocity uses the current full angular rate. It writes reciprocal contact
records on the first accepted sample, updates both bodies' linear and angular
velocity accumulators, and clears response gates on affected bodies.

The supplied-state response is translated in Python at
[`client/collision_pair_response.py`](../client/collision_pair_response.py) and
in C++ at [`native/src/collision_pair_response.cpp`](../native/src/collision_pair_response.cpp).
The Python version is compared directly with the original in
[`collision-helper comparison`](calculations/collision-helpers.md): 256
deterministic cases cover rotated bases, angular motion, movement modes and gate
states, with maximum final-velocity error below `1e-6`. This does not recover
the contact producer or caller's shape sampling, nor does it complete terrain
collision, damage, event delivery, pair ordering or the integrated collision
tick. Native/Python output parity is separately checked over the same corpus;
neither comparison establishes live-game collision behavior.

The oriented-box resolver at `0x45af30` is now translated in Python and C++.
Its four geometry helpers, ordered point sampling, movement gates,
mass-weighted 32-step center-line correction and 22-vertex mode-6 refresh were
checked against 128 direct original calls; position and vertex error stayed
below `6.7e-6`. Render-cache global side effects and other dispatch variants
remain outside the pair result. Its support-point caller `0x459150` transforms
22 local points and applies terrain-plane corrections. The shared vector-array
translation helper `0x6f1450` is now recovered and checked directly, but the
terrain query and full support/contact producer chain remain open.

## Remaining work

- Recover the data types and producers for collision object shapes, triangles,
  terrain queries, rotations, global candidates and shared contact records.
- Recover and compare `0x45cf70`, `0x45d1f0`, `0x45c3e0`, task-list
  execution, and the recurring game-frame caller.
- Integrate the dispatcher and pair paths with ordered callbacks and byte-level
  contact-record checks; then compare controlled original trajectories.
- Integrate it with the force vehicle state and test wall/resting impacts,
  object pairs, terrain contacts, repeated contact persistence and tunnelling.

Until those steps pass, the playable driving mode's prototype collision
behavior and all original collision acceptance gates remain open.

The single-body support impulse helper called by `0x459150` is also translated
in Python and C++ at `0x457df0`. It covers impulse accumulation and its support
contact record from supplied body, point and normal data; 128 direct original
cases and the matching native/Python corpus pass. The terrain query, support
point correction and complete `0x459150` caller remain unresolved.

Additional static inspection of `0x459150` narrows the remaining port boundary.
It transforms 22 local points by the object's 3x3 orientation, selects points
whose transformed local Y is nonpositive, and copies a 0x44-byte per-point
query seed from the object's `+0x370` table before calling `0x42e760` at each
world-space point. For successful queries it normalizes the first three
surface coefficients, tests the point against the returned surface reference
and a one-step vertical-motion allowance, and may translate the object and
all 22 transformed points together. A second pass evaluates eligible support
contacts through `0x457df0` with per-surface coefficients. This is a static
control-flow recovery only: byte-for-byte query-seed semantics, the complete
second-pass memory layout, and caller-level dynamic equivalence still need a
portable implementation and direct original comparison.

The observed dispatcher order now has a bounded Python source translation in
[`client/collision_dispatch.py`](../client/collision_dispatch.py), documented
with its explicit child and global-state boundaries in
[`collision-dispatch.md`](calculations/collision-dispatch.md). It has focused
unit coverage but no direct original-execution comparison yet; this does not
complete the collision chain above.
