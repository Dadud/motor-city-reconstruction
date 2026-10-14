# Original collision calculation helpers

Three bounded helpers now have authored Python/C++ implementations. They consume
supplied contact/body data. Contact discovery, complete terrain/object response,
damage, recovery and the integrated collision tick remain unfinished.

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
