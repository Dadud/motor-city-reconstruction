# Original collision calculation helpers

Four bounded helpers now have authored Python/C++ implementations. They consume
supplied contact/body data. The original caller order and object-pair contact
response have now been traced in [the collision update](../collision-world.md),
but that enclosing path has no portable implementation or trajectory comparison
yet. Contact discovery, complete terrain/object response, damage, recovery and
the integrated collision tick remain unfinished.

Source: x86 `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA evidence: response `0x458390`
`ev_f832418b8121822c838a2b72da7bc532fff1ff5e52a4268711132e810d930c9f`,
impulse `0x457780`
`ev_53e272c26a37a9dde3dd1e356e7c2431a9deefbbcbb11fc0e5733319c94bc9b8`,
plane height `0x4b71a0`
`ev_1b6c7740325541f1d50a0ae294a0193ef2942e38b6511b608652c132b0125efb`.
No original instruction bytes or decompiler output are distributed.

## Response vector and status

For supplied relative vector `v` and normal `n`, `0x458390` computes approach
`a = −dot(v,n)`. If its extended result is nonpositive, return status 0 and zero
vector. Otherwise store `a` float32, form stored projection `a × n`, and subtract
that from `v`. The original normal is consumed directly, without normalization.
These literal signs must be preserved; this helper alone does not establish
a conventional friction decomposition or the caller's coordinate convention.

Normalize the nonzero remainder and negate its stored unit direction. Compare
its stored length `l` against supplied threshold coefficient times stored `a`.
If the latter is smaller, return status 2 and the negative unit direction scaled
by stored `sliding_coefficient × a`. Otherwise return status 1 and that direction
scaled by `l`. Zero remainder returns status 0. Coefficient producers and physical
interpretation remain unresolved.

## Impulse-to-motion helper

`0x457780` takes supplied impulse vector, lever, radial direction, inverse mass,
body inverse inertia and two transforms. With positive extended approach
`−dot(impulse, radial_direction)`, normalize the impulse and multiply by inverse
mass and the stored approach to produce linear response; otherwise linear
response is zero. Angular response is computed in both branches:

```text
world_moment = lever × impulse
body_moment = world_to_body(world_moment)
body_angular = body_moment × supplied_inverse_inertia_per_axis
world_angular = body_to_world(body_angular)
```

Original cross-product and transform storage boundaries are retained. The
helper applies no timestep. It does not create the impact impulse, choose
restitution or establish normalization of radial direction. No simulation
integration or physical unit conversion is inferred from this bounded API.

## Plane height

For normal `(nx,ny,nz)`, plane point `p` and query position `q`, `0x4b71a0`
returns the height:

```text
height = py - ((qz-pz) × nz + (qx-px) × nx) / ny
```

For normal `(0,1,0)` and plane point height 20, every query returns 20. The
comparison stores the original x87 result to float32 like the authored API.
The original divides directly; the public helper rejects `ny=0` because a
vertical plane has no unique height. That rejection is an authored boundary.
Callers can retain the x87 return in the FPU stack instead of storing it to a
float. The `0x51e940` contact-clearance loop does exactly that through its
subtraction, rounding only the final clearance. The integrated implementation
uses `track_plane.surface_height` for this path and keeps the float-stored
`collision_impulse.plane_height` API for callers that store the height first.

## Support-point array translation

`client.geometry_transform.add_vector_to_points` translates contiguous
three-float points using the helper at `0x6f1450`; the native counterpart is
`mco::add_vector_to_points`. The original loops the requested count, adds one
shared vector to each point, and supports the in-place source/destination
alias used by its caller. Across 128 direct original calls, counts 0, 1, 2, 22
and 47 and alternating alias/out-of-place buffers matched float-for-float.
The native implementation matches Python across the same corpus, and its
in-place 22-point test passes. The helper is also composed into the bounded
`0x459150` support-correction caller described in
[`collision-world.md`](../collision-world.md); full track and game-tick
equivalence remain open.

## Sampled pair impact

`client/collision_pair_response.py` translates the bounded response body at
`0x458530`. It builds center-of-mass contact levers and radial directions,
selects the effective mass and response gates, samples angular plus linear
point velocity for up to 32 steps, obtains tangential response from
`0x458390`, and applies time-scaled normal/friction impulses through
`0x457780`. It updates both bodies and writes reciprocal first-contact records.
The sample fraction scales the impulses; point velocity uses the current full
angular rate, including changes from earlier samples.

The direct original-execution harness in
`tools/collision_pair_response_oracle.py` compares 256 deterministic synthetic
body pairs, including rotated bases, angular motion, movement modes and gate
states. Impact decisions and discrete reciprocal-record fields match; float
record fields use a tolerance of `max(2e-4, 1e-6 relative)`. Maximum absolute
final-velocity error is `9.5367431640625e-7` in this corpus. This bounds the
supplied-state response routine only. Its callers,
contact discovery, terrain response, persistence, event delivery, and complete
game collision tick remain unresolved. The native C++ translation also matches
Python across the same 256 cases, with maximum absolute output error below
`5.1e-6`, using `tools/native_collision_pair_response_compare.py` and the
`mco_collision_pair_response_compare` runner. Neither comparison establishes
live-game behavior.

## Single-body support impulse

`resolve_surface_impulse` translates the supplied-state body path at `0x457df0`,
which `0x459150` calls after correcting support points. It derives the center-of-
mass lever and radial direction, samples the body's current point velocity for
up to 32 steps, computes normal and tangential response, applies time-scaled
impulses through `0x457780`, and writes the support contact record on the first
inward sample. The embedded pointer stored at body `+0x404` is represented as
input state; contact discovery and the caller's terrain correction are not part
of this helper.

The direct original-execution comparison in `tools/surface_impulse_oracle.py`
passes 128 deterministic supplied-state cases. Discrete decisions and contact
record integers match; floats use a tolerance of `max(2e-4, 1e-6 relative)`,
with maximum absolute output error `0.000244140625`. The native translation
matches Python across the same corpus with maximum absolute output error
`4.921875188301783e-6`. These bounded checks do not establish full terrain
support, contact discovery, or complete `0x459150` behavior.

## Verification and remaining collision work

```powershell
python -m tools.collision_response_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m tools.collision_impulse_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m tools.native_driving_compare build/native-check
```

The complete response helper passes 1,731 original cases exactly, covering all
three statuses and checking unchanged inputs. The complete impulse helper
passes 1,920 cases exactly; plane height passes 48 float-stored cases exactly.
Native/Python corpora also match exactly. These compare real original helpers
with supplied body/contact state rather than substituted physical formulas.

The enclosing terrain `0x45a320`, object `0x458530/0x459150` and dispatcher
`0x45abe0` routines still need their full dependency chains: triangle selection
and normals, broad-phase/overlap tests, contact persistence, impulse creation,
component damage and recovery, event delivery, pair ordering and tick execution.
Passing these helper comparisons does not prove resting contact, wall impacts,
vehicle pairs or tunnelling acceptance scenarios.
