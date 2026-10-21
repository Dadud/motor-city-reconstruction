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

`0x45a320` immediately accepts an object with nonzero `+0x6c`; objects with
byte `+0x6` delegate to `0x54f0e0` and return whether it reports a hit. Other
objects select a fixed triangle-index table by shape value at `+0xdc`: 12
entries for shapes 0 and 2, 6 for shape 1, and 40 for shapes 3 and 4. For each
triangle, the routine applies three signed projected-edge tests against the
object's `+8/+0x10` coordinates, then calls `0x6f14f0` on the triangle edges.
When all three edge queries pass, it copies the triangle into a per-candidate
buffer, clones the object's 0x44-byte surface-query seed at `+0x370`, and
queries each of the triangle's three vertices through `0x42e760`. A zero query
result takes the object's plane at `+0x328/+0x340`; otherwise `0x42dc50`
supplies a vertex plane. Heights are evaluated by `0x4b71a0`; deviations over
0.5 are replaced with the object plane. The candidate is discarded when the
minimum of the three signed distances exceeds 0.1016.

For retained candidates, the routine constructs a contact normal from object
rotation/rate fields, candidate geometry and object velocity using vector
helpers `0x6f3b75` and `0x6f1140`. It accepts up to three vertices whose computed
speed-like value is below 0.1016 (and caps the stack collection at 36 bytes),
then passes the accepted point arrays to `0x459e30` to derive response vectors.
The routine updates response accumulators at `+0x408/+0x40c`; when the height
minimum is nonpositive, it translates position and the object's plane origin,
clears `+0x350`, and may further correct position along the object plane.
Finally it scales the two coefficients at `0x89c0a8/0x89c0ac` by `+0x318`
and response mode `+0x354`, calls `0x457550`, and returns true. Unknown shape
values log an error; the decompiled default branch's later table use is not a
safe portable behavior.

This is static evidence, not a source translation: triangle-index data,
triangle-boundary behavior on degenerate geometry, helper conventions, global
coefficient values, `0x54f0e0`, and output mutations require bounded direct-call
coverage. The separate support-correction caller `0x459150` is translated and
validated below; its terrain producer and the complete `0x45a320` query remain
unported.

The first early candidate gate is translated in
[`client/collision_terrain.py`](../client/collision_terrain.py): it applies the
three float32 signed XZ inequalities and rejects a zero-length consecutive 3D
edge, matching `0x6f14f0` (`ev_3085534cf4a25e13bc6d0962322d24f2d08c453f2348dea191ade8bb4a3b53a0`).
Five rejected shape-0 cases execute the actual `0x45a320` entry and return
false without mutating the supplied object image: four bypass both the edge
helper and terrain query; the degenerate shared-edge case reaches the
zero-length helper once for each of 12 candidates and never queries terrain.
Run
`python -m tools.collision_terrain_gate_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"`.
This narrow harness does not execute accepted candidates or establish any
terrain-height, response, specialized-object or live-world behavior. The
current caller dossier is `ev_9cf820fb1aeb7a29be3792227239586b1772b50c8b982c9a3745c5178c6bd6ca`.

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
translation helper `0x6f1450` is now recovered and checked directly, while the
terrain query and full collision contact-producer chain remain open.

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
cases and the matching native/Python corpus pass. The terrain collision producer `0x45a320` and complete collision integration remain unresolved.

`0x459150` transforms 22 local points by the object's 3x3 orientation, selects
points whose transformed local Y is nonpositive, and copies the 0x44-byte query
seed at object `+0x370` into a separate stack record for each selected point.
Each world-space point is passed to `0x42e760`. Successful queries supply the
surface coefficients, descriptor and first-vertex pointers used by a signed
plane test and one-step vertical-motion allowance. Penetration can translate
the object and its 22-point world buffer. A second pass checks corrected point
distances, selects material coefficients from the descriptor type and calls
`0x457df0`; successful impulses update the support count and material field.

Python now composes both passes in
[`client/collision_support.py`](../client/collision_support.py). The direct
original-execution harness `tools/support_correction_oracle.py` ran the actual
`0x459150` entry and its real lookup, point-translation and impulse callees in
256 supplied-world cases. It compared return counts, corrected positions,
linear/angular velocities, all 22 world support points, discrete contact
fields and recorded contact floats. The cases included 89 position corrections
and 39 successful impulses; maximum absolute error among compared floats was
`4.76837158203125e-7` (acceptance tolerance `max(4e-4, 2e-5 relative)`). This
is bounded synthetic-world evidence, not complete live-track or game-tick
equivalence.

The native C++ first/second-pass implementation is in
[`native/src/collision_support.cpp`](../native/src/collision_support.cpp) and
builds as part of `mco_core`. The native/Python comparison covers the same 256
worlds and all compared outputs, with maximum absolute error
`4.897460925690211e-8`. Its direct original comparison is still pending; the
256-case original check currently executes the translated Python composition
against the original caller.
The observed dispatcher order now has a bounded Python source translation in
[`client/collision_dispatch.py`](../client/collision_dispatch.py), documented
with its explicit child and global-state boundaries in
[`collision-dispatch.md`](calculations/collision-dispatch.md). It has focused
unit coverage but no direct original-execution comparison yet; this does not
complete the collision chain above.
