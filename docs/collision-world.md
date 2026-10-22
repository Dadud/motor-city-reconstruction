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

The dynamic candidate loop in `0x45cf70` consumes the separate record table at
`0x97c410`, bounded by the count at `0x97c398`. It skips entries whose float
fields at `+0x30` or `+0x74` are zero, transforms the record's local center at `+0x4c`
through its matrix at `+0x0c`, and admits a pair when squared center distance
is no greater than the square of owner radius `+0xd8` plus record radius
`+0x48`. This prefilter is translated in
[`client/collision_pair_candidate.py`](../client/collision_pair_candidate.py).
The direct original harness executes the real `0x45cf70` path for 512 varied
records and body positions; 134 reach `0x45af30`, and all eligibility, boundary
and first-rejection outcomes match. With `--execute-pair-resolver`, the same
original path runs the real `0x45af30` resolver: 35 pairs produced 83 calls and
33 calls to `0x458530`, matching the translated retry loop and final body
centers. This includes the 33-call cap when a coincident pair cannot separate.
The harness also seeds one approaching pair and compares the integrated
response velocities and reciprocal contact records with the translated
`0x458530`; one of the 33 response calls applies a nonzero impulse. Dynamic
candidate-record production remains untranslated. Original function dossier:
`ev_bc440ea786fb8140385b6eb99b24d3af70ca0fa66b5794d68152e16e25b75471`.
Run `python -m tools.collision_pair_candidate_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 512`
for the broadphase, or add `--execute-pair-resolver --cases 128` to check
resolver retries and integrated pair response against native execution.

## Sampled world-contact pass

`0x45d1f0` scans the sampled candidate records owned by the selected world
object. The translated prefilter checks a horizontal radius, a vertical
threshold, and projections against the object's three local extents expanded
by the decoded vertical value. Its pure decoder `0x42db70` reads signed 16.16
coordinates from each 0x14-byte record, converts a signed short field according
to the low two type bits, and returns a type-dependent radius (3, 12, 2, or 1).
That decoder is translated in
[`client/collision_world_candidate.py`](../client/collision_world_candidate.py)
and matches 256 original calls, including 204 valid indices, in
[`tools/collision_world_sample_oracle.py`](../tools/collision_world_sample_oracle.py).
The `0x45d1f0` prefilter matches 512 original calls, with 348 reaching a stubbed
`0x42d9f0` classifier, in
[`tools/collision_world_prefilter_oracle.py`](../tools/collision_world_prefilter_oracle.py).
The classifier maps sample kinds 1 and 3 to distinct response codes; kind 2
uses a per-sample state byte and a speed gate to decide whether to request a
runtime trigger. `update_world_contact` composes classification, allocation
and sample-state writes. 128 direct original calls now execute the real
allocator, heading helper and writer; the translated path matches the return
decision, type code, all three sample-state bytes, and all `0x1800` trigger-slot
bytes, including missing resources and signed-byte slot-index boundaries. The
256-entry allocator at
`0x407710` is translated in the same module and matches 128 original calls
across its return value and all `0x1800` slot bytes. The heading helper
`0x6f2cc0` is translated in
[`client/collision_heading.py`](../client/collision_heading.py), including its
257-entry table at `0x8c8d10`, Q32 ratio, interpolation and signed octant
folding. Its result matches 4,096 direct original calls, including zero, axes,
all octants and full-range signed coordinates. The classifier derives and
stores the saved angle byte itself.

For classifier decision 2, the enclosing `0x45d1f0` caller has an additional
strict timer gate: when body `+0x3b4` is greater than 2, it clears the contact
impulse vector, writes `mass * 15` as contact magnitude, records the decoded
sample X/Z and body Y, stores type `0x1a`, and marks contact mode 5. This state
update is translated by
[`apply_world_decision_two_contact_cache`](../client/collision_world_response.py)
and compared through the real classifier and full caller in
[`tools/collision_world_decision_two_oracle.py`](../tools/collision_world_decision_two_oracle.py):
128 executions matched the complete 0x400-byte body image, 96 with the timer
gate active. The decision-1 handler lookup and shared contact-event method are
now translated in [`client/collision_event.py`](../client/collision_event.py).
The direct harness [`tools/collision_event_oracle.py`](../tools/collision_event_oracle.py)
compares 256 executions of lookup `0x43b550`, method `0x4658f0`, and sampled
callback `0x465a00` byte-for-byte. Inspection of the actual vtables shows that
the caller's `+0x14` slot is `0x465a00`; it invokes `0x4658c0`, which toggles
the event state through `0x465850`/`0x465880`, then stores sample data in the
body and increments the handler count when activation succeeds. The full
caller harness [`tools/collision_world_event_dispatch_oracle.py`](../tools/collision_world_event_dispatch_oracle.py)
matched 128 `0x45d1f0` executions, including all event fields and handler
counters: 64 queued events, exact positions, and maximum velocity error
`2.384185791015625e-7`. It stubs `0x487490`; audio behavior remains open.

The kind-1 decision-1 path is also composed through the actual caller. It forms
a horizontal normal from the body to the sample, offsets the sample by its
decoded vertical value, and calls `0x459940` with the 8/22-point geometry and
the caller's 0.25 response coefficients. If the response records a nonzero
contact magnitude, it writes sample X/Z, body Y, type `0x1d` and contact mode 5
to the body cache. `resolve_world_decision_one_sample` models this complete
path. The direct harness [`tools/collision_world_decision_one_oracle.py`](../tools/collision_world_decision_one_oracle.py)
matched 128 full `0x45d1f0` executions: 64 impacts updated the cache and 64
receding cases did not. Position and checked contact/cache bytes matched
exactly; maximum linear-velocity error was `2.384185791015625e-7`. The
conditional virtual event dispatch is verified above. For classifier result
`-1`, the caller builds a temporary `0x418`-byte body with dimensions
`(vertical, 3, vertical)`, places it at the sample, normalizes the horizontal
body-to-sample direction, and calls `0x458530`. A successful result clears
`+0x3c4`, records type `0x19` and mode 5, and stores the counter-derived
contact magnitude. This path is translated in
[`client/collision_world_pair.py`](../client/collision_world_pair.py).
[`tools/collision_world_decision_minus_one_oracle.py`](../tools/collision_world_decision_minus_one_oracle.py)
matched 128 executions through the original caller with the real `0x42d9f0`
classifier, allocator, heading helper and writer. All 128 reached the pair
solver, 64 applied impacts, sample-state and complete trigger-slot memory
matched exactly, and maximum velocity error was `7.152557373046875e-7`.
The isolated-response mode still supports forcing `0x42d9f0` to return `-1`;
pair coefficients remain supplied inputs. The zero-height proxy also matches
128 original caller executions. Its
zero X/Z dimensions produce infinite inverse inertia on one axis; native IEEE
propagation yields NaN owner angular velocity while leaving linear velocity
unchanged. The model preserves that behavior instead of rejecting the
singular inertia. Dynamic candidate-record production remains open.

The table loader `0x407570` reads seven `TRxx.CAN` archives and converts the
first three signed words of each 20-byte record. The portable decoder in
[`client/collision_trigger_resources.py`](../client/collision_trigger_resources.py)
matches the original x87 precision and spill order. Direct tests run 128
synthetic loader cases plus the seven installed game files through the original
entry, covering 833 synthetic archive loads and the full record arrays in all
of them, plus 7 real archives. The installed files declare 51, 41, 6, 17, 94,
51 and 41 records in `TR00A.CAN`, `TR01.CAN` through `TR06.CAN`. The
loader's path formatting and file-system calls are supplied at the oracle
boundary; archive bytes and loader conversion run against original code.
Resource pointer assignment into a running world-contact pass and later
terrain/pair response branches remain open. REA evidence for the allocator is
`ev_1fc62bee4bb96955164d683b40e8efd30e167ca68d4f92d818105f47699ec40a`; evidence
for the decoder is
`ev_749a6f637a87befe4bb4b17391d5da66a1df08fcc17d6cd2aa928b5584d1f817`; the
parent scan dossier is `ev_015e1c891236317830cd6ece8baeca1407618a691fc1217708d18d4b55588cc3`,
and the classifier dossier is `ev_d09a06a7ee2100329b216861b76be32a690125ccb087bc12ccea9b1e67d32d73`.
The heading implementation, shift/divide helpers and lookup table are
documented by REA evidence `ev_14e2213c297f683faf8b589f0daa55b2f416c4ef04025a735e9c5af8a44b0118`,
`ev_4e38e82401d138ab78e2db02a11cda6604616eb12346b628da1ba2adb7f83b2c`,
`ev_792ebf8adbd8a8da20d37072a0576d2f658a3d61a013138fd0454009b3e88eb3`
and `ev_d1235e464bb2b08047606037ab52105f2db295cc304a4a359f74cb41e55a40de`.
Run `python -m tools.collision_heading_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 4096`
to compare the integer heading helper directly. Run
`python -m tools.collision_trigger_resources_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 128 --data-root "C:/Program Files (x86)/EA Games/Motor City Online/Data/GameArt"`
to compare archive loading and coordinate conversion with the original entry.
Run `python -m tools.collision_world_trigger_update_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 128`
to compare the composed trigger allocation and notification state.

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

The ordered shape tables are decoded in the Python translation and checked
against the executable. The three-vertex motion predictor and its
caller-side velocity/rate cleanup are also translated and compared over 64
direct executions of `0x45a320` with varied body velocities, angular rates,
center of mass and orientation. The specialized `0x54f0e0` transform and
projected gate have separate bounded direct-call coverage below; shape-table
candidate selection over nondegenerate meshes and broad output equivalence
remain open. The separate support-correction
caller `0x459150` is translated and validated below; most of the `0x45a320`
query remains unported.

The `0x54f0e0` specialized branch now has a Python translation of its four-point
mode-6 transform and projected XZ gate in
`specialized_quad_projection_candidate` and `specialized_quad_projection_gate`.
It checks the quad as two triangles split across corners 0 and 2, preserving the
original inclusive edge rejection, and forwards the larger geometry extent. A
128-case original-entry harness compares every transformed corner and gate
decision with the executable: 105 cases return before the inner worker and 23
delegate with matching corner data and bound. In this harness only, the
`0x54f2a0` inner worker is stubbed to return true, so the test establishes the
transform, projected gate and forwarding behavior, not collision response
inside that worker. The native CPU-specific dispatch implementation itself is
outside the translation. The original `0x54f0e0` and `0x6f1320` analysis records are
`ev_fa6ee44ac7b009dcafb034957c75ce2a9af35ef938230fd7a3f15cf32b01382f` and
`ev_65a4dbd1df45dd1b34e1e7da31cd7cdb3affb0a023a110e4700f17b7ec14fb30`.
Run
`python -m tools.terrain_specialized_quad_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 128`.

The `0x54f2a0` worker's four-corner surface sampling and height acceptance are
also translated. `sample_specialized_quad_heights` composes the bounded track
lookup and plane queries with `specialized_quad_height_gate`: gaps outside
`[-0.5, 0.5]` use the owning object's plane, then the minimum gap is compared
with the forwarded geometry extent. Sixty-four direct original calls vary
corner heights, XZ positions and the extent; all reject with minimum gaps from
`0.5` to `1.5`. Together they make 256 `0x42e760` lookups, 256 `0x42dc50`
plane queries and 458 `0x4b71a0` evaluations, skip the motion/response helpers,
and clear the worker's 24-byte six-word record on each rejection. Run
`python -m tools.terrain_specialized_height_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"`.
Evidence for the original worker is
`ev_83bcd3e2b0527b9514e1e7da31cd7cdb3affb0a023a110e4700f17b7ec14fb30`.
The point-to-center-of-mass helper called once for each corner is also
translated by `terrain_contact_lever_arm`. Its 515 direct original comparisons
vary the position, local center, supplied body basis and point; maximum absolute
error is `1.9073486328125e-6`. Run
`python -m tools.terrain_contact_lever_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"`.
The worker's four-corner motion filter now has a translation in
`specialized_quad_contact_selection`, followed by the first response-axis
projection in `specialized_quad_response_axes`. `specialized_quad_contact_selection`
uses the sampled contact heights for motion prediction and source points, while
the offset-adjusted points retain input vertex heights. On 2,055 direct original
calls, 1,258 select at least three corners and 797 reject on predicted motion.
Every return decision and both three-point arrays passed to `0x459e30` match.
For accepted cases, the owner response-axis fields `+0xc00`, `+0xc04`, `+0xbfc`,
`+0xbf4` and `+0xbf8` match within `2.9802322387695312e-8`. The suspension
response tail is translated in `specialized_quad_response_dynamics`; angular
velocity, linear velocity, position correction and the `+0x350` contact-state
clear match within `5.960464477539063e-8` (the status word matches exactly).
The corpus varies sampled corner heights from `-0.2` through `0.2`, per-corner
offsets around the motion threshold, and suspension geometry/response
coefficients by a deterministic scale from `0.75` through `1.23`; accepted
cases include sloped contact triplets and negative gaps that exercise positional
correction. The near-zero roll branch uses a small tie window because float32
angle calculations can reverse the native sign at zero. Run
`python -m tools.terrain_specialized_contact_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 2048`.

The three triangle tables at `0x88c9d4`, `0x88ca64` and `0x88c7f4` contain 12
ordered triangles for shapes 0/2, 6 for shape 1, and 40 for shapes 3/4. Their
indices are retained in `terrain_shape_triangle_indices`; the REA byte reads
are `ev_7f990f062baa97300b2aaee6be5780fef61245b1742d10ab57f50b1102e09dbc`,
`ev_4c554a0146d1cd355fcb9a5ffb1c636b7ac74a9320fa6f4606f4885b5f8fa512`, and
`ev_c4b08d09aa31a238c15fac69764030037ab0f2a42c55a6d04a0a46f70de3900e`.
The table oracle compares all decoded indices with the original executable and
executes `0x45a320` for shapes 0 through 4 on a degenerate mesh; the original
visits exactly 12, 6, 12, 40 and 40 candidates, respectively, then returns
false without changing the supplied body. Run
`python -m tools.terrain_shape_table_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"`.

The first early candidate gate is translated in
[`client/collision_terrain.py`](../client/collision_terrain.py): it applies the
shape table in original order, then the three float32 signed XZ inequalities,
and rejects a zero-length consecutive 3D edge, matching `0x6f14f0`
(`ev_3085534cf4a25e13bc6d0962322d24f2d08c453f2348dea191ade8bb4a3b53a0`).
Five rejected shape-0 cases execute the actual `0x45a320` entry and return
false without mutating the supplied object image: four bypass both the edge
helper and terrain query; the degenerate shared-edge case reaches the
zero-length helper once for each of 12 candidates and never queries terrain.
Run
`python -m tools.collision_terrain_gate_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"`.
This narrow harness does not execute accepted candidates or establish any
terrain-height, response, specialized-object or live-world behavior. The
current caller dossier is `ev_9cf820fb1aeb7a29be3792227239586b1772b50c8b982c9a3745c5178c6bd6ca`.

The same module translates the three-vertex height filter: each signed gap is
`vertex_y - sampled_height`; gaps outside `[-0.5, 0.5]` use the object-plane
height instead, and the candidate is rejected when the minimum gap is above
`0.1016`. One flat supplied-world case exercises the actual caller with three
`0x42e760` lookups and three `0x42dc50` plane queries, confirming rejection
before `0x457550` and no object mutation. Its sampled and fallback heights are
produced by the Python track lookup/plane composition and passed through the
height filter. Run
`python -m tools.terrain_candidate_height_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"`.

The accepted-candidate normal helper `0x459e30`
(`ev_68a8ef9c98355d85f293f808bb9ece61329e4891ca5db1018c235e20427e321b`) is
translated as `terrain_response_normal` and matched 261 direct original calls
with maximum absolute error `1.4901161193847656e-7`. The body response helper
`0x457550` (`ev_83c698b2ec1c4b875f84246b3e11dbbbf6a676b523333c3bff83c55949ff0684`) is
translated as `terrain_impact_response`; 260 supplied-state original calls
matched with maximum absolute error `0.0001220703125` under a magnitude-scaled
tolerance. An accepted supplied-world triangle also runs through the actual
`0x45a320` entry across 512 varied linear/angular velocity states: each case
performs three terrain/plane queries, calls `0x459e30` twice and `0x457550`
once, and matches the helper's captured normal, status, final velocity and
tangential contact record with maximum response error `7.62939453125e-6`
under a magnitude-scaled tolerance. The other body bytes remain unchanged in
every fixture. A rising-body case rejects at the caller's motion gate before
either response helper. Run
`python -m tools.terrain_response_normal_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"` and
`python -m tools.terrain_impact_response_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"` for the helper comparisons, or
`python -m tools.terrain_candidate_impact_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 512` for the enclosing accepted-candidate cases. The motion predictor and caller-side cleanup run in
`python -m tools.terrain_candidate_motion_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 64`; all 64 cases match the original entry's accept/reject result and helper-call path, and accepted cases match final linear/angular velocity. Live-world behavior and broad output equivalence remain open.

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

The four-edge contact-mask helper `0x42d900` and edge-contact selector
`0x45c870`, called by the object-pair dispatcher `0x45c3e0`, are now translated
in [`client/collision_edge_contact.py`](../client/collision_edge_contact.py).
They compare the query against four ordered XZ edges, then select a contact
vertex and average enabled edge normals and height weights. The direct oracle
[`tools/collision_edge_contact_oracle.py`](../tools/collision_edge_contact_oracle.py)
matched all 256 masks and selector calls; 205 returned accepted contacts, with
maximum output error `3.814697265625e-6`.

The dispatcher’s earlier object and height gates are now translated in
[`client/collision_pair_gate.py`](../client/collision_pair_gate.py):
`0x42d890` checks identity against the owner’s eight contact links, while
`0x45cd80` applies a material-dependent maximum-vertex-height rejection.
[`tools/collision_pair_gate_oracle.py`](../tools/collision_pair_gate_oracle.py)
matched 256 direct original calls, including 35 vertical rejects. The world
table and the four candidate vertex records were explicit inputs to those leaf
checks. The full track-query dispatcher is now translated in
[`client/collision_pair_dispatch.py`](../client/collision_pair_dispatch.py).
It runs the original two surface queries for each extracted body point, uses
the supplied track blocks and path table, applies the gates and edge selector,
classifies the selected contact through the path row, scales the recovered
material coefficients, and invokes the plane response. Its swept pose composes
`0x520110` and the Euler-matrix update from `0x4b7430`.

The controlled oracle
[`tools/collision_pair_dispatch_oracle.py`](../tools/collision_pair_dispatch_oracle.py)
compared 256 direct calls to the swept-pose helper and 128 complete original
`0x45c3e0` calls. The corpus produced 102 responses; body-state discrete bytes
matched, the maximum pose error was `1.9073486328125e-6`, and dispatcher float
fields matched within `max(3e-5, 3e-6 relative)` (maximum absolute error
`0.0078125`). These results cover supplied adjacent-track fixtures under
controlled original-instruction execution; they do not establish live-game or
whole-frame behavior. The virtual event target and other runtime candidate
sources remain open.

The dynamic-pair candidate table producer `0x427f50` is translated in
[`client/collision_pair_candidate.py`](../client/collision_pair_candidate.py).
It consumes explicit 0x38-byte source rows and their packed vertex arrays,
then builds the parallel 0x78-byte candidate rows with local bounds, center,
bounding radius, copied metadata, source type mutation, and back-link. The
controlled original-entry harness
[`tools/collision_dynamic_candidate_table_oracle.py`](../tools/collision_dynamic_candidate_table_oracle.py)
matched every output-table and mutated-source byte in 128 cases. The original
producer body ran with fixed-address allocation and exact-range zeroing bridges;
allocator policies and upstream candidate roster production remain explicit
runtime inputs.

Its downstream spatial marking helpers are translated in
[`client/collision_spatial_hash.py`](../client/collision_spatial_hash.py).
The `0x426af0` radius predicate and `0x426b40` linked-cell walk match 128 and
256 controlled original calls, respectively. The `0x426bc0` pass scans each
active body's own hash bucket and eight signed neighbor slots, marking inactive
overlapping objects; 128 original calls over 816 body records matched all
record bytes. The complete `0x426770` rebuild now composes those gates with the
body sleep filters, head-inserted hash links, active-roster pass, dynamic
candidate rows, nine-cell marking pass, and inactive-body cache clearing. Its
original-entry harness compared all bytes of 696 body records over 128
supplied-world cases, including 380 active-roster entries and 192 dynamic
candidates. The body array, roster, neighbor cells and candidate table remain
explicit runtime inputs; their producers and world-scale tick integration are
still open.

The loader's palette pass is reconstructed in
[`client/collision_palette.py`](../client/collision_palette.py). The `0x428500`
helper applies three signed-int32 percentage scales to packed RGB bytes while
preserving alpha; `0x428640` walks pointer-based groups and applies the same
transform to each palette. The original routines matched 7,853 direct color
words and 1,778 words reached through 128 group-list calls. This recovers the
helper behavior only; world-file layout and resource loading in `0x428150`
remain incomplete.

The variable-section pointer fixup used by the same loader is implemented in
[`client/world_dataset_layout.py`](../client/world_dataset_layout.py). The
`0x428680` translation lays out 0x38-byte rows, nullable payload pointers,
vertex arrays, trailing per-vertex values, triangle arrays and the observed
two-byte odd-count alignment. In 256 direct original calls, all supplied image
bytes and the final global cursor matched across 1,165 rows and 24 empty
sections. The caller's file-buffer and section ownership logic remain open.

The next loader stage, per-world-object initialization at `0x426d50`, now has a
bounded source translation in
[`client/world_body_initialization.py`](../client/world_body_initialization.py).
It normalizes descriptor mass and extents, maps shape/material selectors,
constructs the base body, initializes the surface-query record, restores the
descriptor pose, handles optional point rotation, and applies the final body
scalars. 256 executions of the original matched every byte of the 0x4f8-byte
object, including cases that execute the original 0.5-turn matrix builder and
inline point transform. The surface query (`0x42e760`), contact setup
(`0x51e460`) and selected geometry callback (`0x6f28f0`) were intercepted as
child boundaries; their effects and actual world data remain unresolved. Their
interfaces stay explicit in the Python implementation. The oracle's stack tail
for the 0x44-byte query record is zero-initialized; the translation accepts an
explicit initial image because the native initializer itself writes only the
first eight words before invoking the query child.

The preceding `0x428710` object-table loop is translated in
[`client/world_object_table_setup.py`](../client/world_object_table_setup.py).
For each supplied source row, it copies 0xa8 descriptor bytes into the object
at +0x418, clears +0x4c0 and the 0x24-byte block at +0x4c8, invokes the body
initializer, then replaces the row's +0x20 source pointer with the object
address. 128 original runs over 255 rows matched every object and row byte;
the `0x426d50` body initializer and `0x6ee0c0` clear child were intercepted.
World-file allocation, pointer-table production and the completed initializer
remain caller inputs.

The response child `0x459b90` is translated in
[`client/collision_pair_surface.py`](../client/collision_pair_surface.py).
It transforms the body's 8- or 22-point set, selects the deepest eligible
inward vertex, corrects penetration and cached world points, then delegates to
the recovered support impulse. Its direct oracle matched 512 original calls:
448 selected vertices and corrected position, and 320 applied impulses. The
maximum observed float error was `0.000244140625`. The supplied plane and body
response now compose into the tested track-query dispatcher. Dynamic object
candidate production and the event callback remain open.

## Remaining work

- Recover the remaining producers and data types for dynamic collision objects,
  terrain triangles, global candidates and shared contact records.
- Integrate the independently verified `0x458530` response with dynamic-pair
  retries; recover upstream candidate-roster production; recover sampled-world
  caller side effects and successful resource-table/heading lookup integration
  in `0x42d9f0`; resolve the dispatcher's virtual callback, task-list execution,
  and the recurring game-frame caller.
- Integrate the dispatcher and pair paths with ordered callbacks and byte-level
  contact-record checks across controlled original trajectories.
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

## Track world-grid relocation

The track mesh decoder returns the byte immediately after its UV/material
tables. That cursor is the input to the original `0x552a00` loader, which
copies the four-float bounds and 64 KiB cell table into global state, computes
the X/Z scale values, then calls recursive helper `0x5529a0` to relocate
pointer/count nodes and leaf identifier arrays in the remaining payload. The
bounded translation is in [`client/world_grid.py`](../client/world_grid.py);
`decode_track_with_spatial` in [`client/track_mesh.py`](../client/track_mesh.py)
joins the existing mesh and query-side spatial decoders.

`tools/world_grid_oracle.py` compared the Python mutation against the original
executable for all 27 installed `Tr.frd` tracks. Each comparison matched all
65,536 table bytes, all mutated payload bytes, bounds, scale floats, and the
final cursor. The corpus manifest is retained locally at
`evidence/session/world-grid-track-corpus.json`. This verifies loader relocation
for the installed assets; leaf identifiers remain opaque and their downstream
collision meaning and complete world-query integration are still open.

## Sampled world vertex response

The response routine `0x459940` receives a plane normal, a plane point, a
distance limit, and the body's point set. It transforms 8 or 22 local points,
selects the nearest point whose plane distance is below the limit and whose
offset from the body center is behind the plane, then corrects penetration.
The correction updates body position and all 22 cached world points before
delegating the impact to `0x457df0`.

The point extractor `0x4596b0` is also translated in
[`extract_world_contact_points`](../client/collision_world_response.py). Its
normal branch copies 66 floats from body offset `+0xe0`; the compact branch is
selected when the signed counter at `+0x3bc` is zero and `abs(+0xc4) > 0.707`,
then constructs eight points from the stored bounds and twelve trailing
coordinates. The direct harness [`tools/collision_world_points_oracle.py`](../tools/collision_world_points_oracle.py)
compared 256 calls, evenly split between both branches, with exact counts and
float bits.

[`client/collision_world_response.py`](../client/collision_world_response.py)
translates that scan and response for supplied point sets. The direct original
harness [`tools/collision_world_response_oracle.py`](../tools/collision_world_response_oracle.py)
matched 128 deterministic cases, evenly split between extracted 8- and 22-point inputs, including penetration corrections,
cached point updates, linear velocity changes, contact-record bytes, and the
routine return. Position corrections matched exactly; velocity error stayed
below `4.2e-7`. Sampled audio/debug notifications remain outside the current
model. The caller-to-event path is now compared through `0x465a00`, its nested
callback, queued body fields, and handler counter; the independent audio/debug
effects remain outside this model.
