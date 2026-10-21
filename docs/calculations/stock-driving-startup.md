# What currently prevents original driving startup

The stock inspector now reads vehicle 101, the Ford 32 V-8 Coupe, together with
the installed Drag track. It loads all four tire, spring and shock assemblies,
engine-block dimensions, decoded wheel markers and terrain under each wheel.
Run it from the source repository:

```powershell
.venv/Scripts/python.exe -m tools.inspect_stock_driving "C:/Program Files (x86)/EA Games/Motor City Online" --output build/stock-driving-inputs.json
```

The report remains outside the original installation. Its `assembled_mechanics`
section now includes complete supported mechanical assembly, total mass, engine
curves, axle levers and gear tables. It distinguishes these recovered values
from measured model geometry and the current authored placement.
The latter raises the car until every tire clears terrain; it does not reproduce
original spawn, suspension compression or the original wheel-support flags.

Original initialization is a larger dependency chain. The recorded `0x43a990`
path calls component assembly `0x54e720`, model/geometry setup, owner binding
`0x53a1f0` and final setup `0x53b8a0`. Component assembly also computes aggregate
values before building the engine curve. Binding engine-block mass as total car
mass, or applying marker spacing as an already verified configuration dimension,
would bypass this chain. Those substitutions are deliberately rejected.

The final wheel setup `0x53b8a0` and its stance adjustment `0x53b3c0` are now
translated in Python and C++. The setup consumes finalized mechanical
configuration, four axle radii, and prior owner geometry; it initializes four
wheel inertia/width/steering records, speed limits, axle positions, and the
stance-adjusted contact coordinates. Exact original execution comparisons cover
56 varied calls and 16 supported assembled stock configurations, comparing the
entire 0x2000-byte owner image. This closes one downstream setup routine, not the
upstream `0x43a990` chain: original model bounds, spawn geometry, resource-backed
area, and complete shared owner initialization remain required.

`client.owner_startup.initialize_owner_startup` now composes the recovered body
phase, complete startup-record constructor, and final wheel setup. It requires
the packed marker-model image and decoded FCE scene nodes separately, since the
former provides wheel-marker lookup while the latter provides projected area.
It also requires pre-existing owner geometry, finalized mechanical configuration
and model half-extents. Focused tests confirm record publication, scene-area
handoff, wheel initialization and refusal of missing prerequisites. This is a
verified-stage composition interface; it does not recover or execute the
original `0x43a990` resource manager, mode selection, loaders, diagnostics or
error-state checks, and no full composite call comparison is claimed yet.

The remaining projected-area input to `0x53a1f0` is model/scene query
`0x483450`. The startup-record constructor now accepts decoded scene nodes and
computes their area with the recovered `scene_area_from_nodes` producer.
`raster_nodes_from_render_list` adapts portable render records, preserving
selected model, surface, and mirror-type fields. This removes the manual area
scalar when a complete selected render list is available. The raw
query traverses registered geometry, projects triangle vertices into a
321x241 occupancy raster, and derives an area-like value from the occupied
pixel bounds and the resulting scale factors. Its helper `0x483f60` is now
translated as `occupied_raster_bounds` in Python and C++. Both ports match seven
direct original masks, including empty/full, all raster corners and randomized
density cases. This recovers only the final nonzero-pixel count and bounding-box
scan. The decoded-geometry overload now assembles the aggregate formula below;
acquiring the native scene registry and completing the raw `0x483450` ABI
remain open. The one-face projection/fill subregion is described below. Run
`python tools/verify_raster_bounds.py <mcity.exe> --native-runner <mco_raster_bounds_compare>`
to repeat the direct comparison. Ghidra evidence for `0x483450` is
`ev_5d14bdb273f285a524a5c7abccfe490e656d8ee1417a69fc711c612e8addc24f`;
`0x483f60` is `ev_97686c2f9566df3c5b00ae50735f4c6ced8127949eed4efeb45082657269f4c0`.
The rasterizer's scanline helpers `0x483f00` (ceil) and `0x483f30` (floor)
are also translated. Both match 256 finite original inputs over the supported
int32 result domain. The edge-intersection and per-face pixel-fill recoveries
are described below. Evidence IDs are
`ev_61d3c8eb4b28922ff4d64ab08c8781bdb9347f19fe98dd7b0232753e37a9a5a4` and
`ev_d850a4269d2a5196363885542a9ebaf064d79d4357aa20acf0ada835a6271f39`.

The rasterizer's vertex-ordering helper `0x483c70` is now translated in Python
and C++. It returns ascending Y while preserving the original's specific tie
choices, including swapping the second and third vertices for a horizontal
triangle. Both ports match 298 direct original calls: all permutations of seven
distinct/tied Y patterns plus 256 randomized triangles. This recovers the
ordering helper; projected edge calculation and pixel fill are covered by the
following entries. Repeat with
`python tools/verify_raster_triangle.py <mcity.exe> --native-runner <mco_raster_triangle_compare>`.
Ghidra pseudocode evidence is
`ev_edd369b79a9607a363cdf85ab7b63301768872845d48aab407951a387e605bec`.

The scanline edge helper `0x483e80` now computes the two line/row
intersections and writes the left X bound followed by the right X bound.
Python and C++ match 517 direct calls, including row endpoints, reversed edge
direction, and 512 randomized overlapping edge pairs. The native port uses
wider intermediates and rounds only when storing the intersections, matching
the original x87 calculation. Horizontal edges remain outside the helper's
domain because the original divides by their zero Y span. The complete
projected-area routine remains partial. The per-face raster portion of
`0x4836f0` is implemented as `rasterize_projected_triangle` in Python and C++.
It projects an assembled XY face through owner bounds, clips to the fixed
raster, rejects zero-area results, selects the two active edges for each
inclusive scanline, and fills inclusive ceil/floor spans. Both ports match the
original mask byte-for-byte on 42 synthetic one-face model records.
`rasterize_scene_geometry` also walks decoded surface records, applies
per-surface translation and the five observed X-mirroring types, filters null
models and types at or above 16, traverses multiple faces, and unions their
pixels. Both ports match 16 direct original linked-scene runs, including a
nonzero surface ID with nonzero vertex and face bases. These tests validate the
observed buffer addressing and traversal for those fixtures. The FCE part
layout has the same origin, vertex-range and triangle-record offsets: new
`raster_meshes_from_nodes` adapters connect decoded FCE parts and scene-node
surface/type metadata to `scene_area_from_nodes` in Python and C++. In the
original object, `owner+0x490` supplies the resource whose `+0x21c` slot yields
the first node; the second cdecl argument is the vehicle index forwarded by
startup and is unused by `0x483450`. `scene_area_from_nodes` accumulates
transformed XY extrema, derives the mask, obtains the inclusive occupied-pixel
rectangle, and applies the original world-area/pixel-density formula. Python
and C++ match the original binary32 return exactly on 19 synthetic linked FCE
scenes using the true two-argument call; the oracle intercepts only
`0x6ee510`/`0x6ee550` and substitutes a deterministic mapped bitmap. Real
resource/node lifetime, allocator semantics, startup wiring and broad
installed-asset coverage remain open. Repeat with
`python tools/verify_raster_fill.py <mcity.exe> --native-runner <mco_raster_fill_compare>`
and
`python tools/verify_raster_scene.py <mcity.exe> --native-runner <mco_raster_scene_compare>`.
For aggregate return values use
`python tools/verify_scene_area_measure.py <mcity.exe> --native-runner <mco_scene_area_measure_compare>`.
Ghidra evidence is
`ev_f41ca7c034d6743711309e8509d3c471bc2e7e1b0dbc90d517cd65a4955e171d`.

Repeat the intersection comparison with
`python tools/verify_raster_intersection.py <mcity.exe> --native-runner <mco_raster_intersection_compare>`.
Ghidra evidence is
`ev_1097cf701c12021465b38c022cd7fe3a2239a4b815833d53b9e85db1fa6a3218`.

The [body numeric initializer](body-configuration.md) now supplies actual
vehicle 101 catalogue configuration: body-base mass 575, wheelbase approximately
2.692, front/rear track approximately 1.4224, front weight fraction approximately
0.4305 and front/rear clearance references approximately 0.28. These appear in
`recovered_body_configuration`, separately from model-marker measurements.
They are original initializer outputs, not completed owner binding or final
assembled mass/inertia. Original semantic validation and body quality remain
outside the bounded comparison.

| Input area | Available now | Still required before faithful startup |
|---|---|---|
| Wheels and suspension | Stock tire dimensions/radius, springs, shocks; decoded marker spacing | Verified owner/configuration dimensions, initial compression, support flags/scales and surface lookup |
| Body and forces | Recovered force consumers and body catalogue initializer | Final whole-car mass, centre of mass, inertia, area/height and initialized transforms |
| Engine and transmission | Engine-block geometry, core dyno reconstruction, recovered consumers | Complete assembled torque table, RPM limits, inertia, gearing/clutch/differential initialization |
| Tires and brakes | Recovered update calculations | Assembled axle curves and coefficients; brake material, capacity, cooling, distribution and initialized state |
| Session and controller | Recovered scheduler/controller order and selected connected stages | Real service/input observations and remaining child implementations on shared state |

The [gear-table binder](gear-binding.md) now recovers speed-per-RPM, wheel
inertia factors and final-drive inertia from finalized rear-tire/gearing inputs.
It matches 225 original cases exactly and supplies two integrated controller
comparisons. Authentic component loaders must still produce the finalized
configuration; these equations do not supply missing stock ratios or mass.

The [mechanical component loaders](mechanical-component-loading.md) now produce
the actual Ford's transmission ratios/losses and final drive, plus engine block,
head, camshaft, crankshaft, rods, pistons, valve-train, rim, spring, shock, brake
and tire configuration, plus intake/exhaust/auxiliary engine, body/accessory and
axle-bar components. Thirty-two loader kinds have matching C++ ports. Tire curves
come from the external auxiliary table. The [complete Python assembly](mechanical-assembly.md)
matches eight stock cars including total mass, quality and engine finalization;
special carburetor/boost modes and native orchestration remain open.
`tools.inspect_stock_mechanical` reports this partial loading with explicit
damage/wear fixture inputs and remaining unsupported component handling. Its mass
accumulator remains incomplete. Use `tools.inspect_stock_assembly` or the
`assembled_mechanics` section of the driving report for finalized mechanical data.

`client.stock_driving_state` exposes these facts and a machine-readable missing
input report. The [assembly numeric finalizer](assembly-finalization.md) now
provides the original component-based weight fraction and numeric postload tail,
with exact original and native comparisons. It consumes loaded component mass
slots; it does not provide missing parts or total mass. This stage precedes owner
binding and complete engine integration.

`construct_observed_state` requires **every** field of a selected
recovered record, including fields with research defaults. Nested wheel, engine
and brake records must be typed explicitly. Supplying a complete observation
record does not establish its provenance; numeric validation remains in the
recovered calculation. `require_recovered_driving` currently fails with the
remaining startup requirements, so this inspection cannot accidentally launch
the prototype handling as recovered driving.

Evidence: original initialization
`ev_1a903ab2ddcafa04ae6b6038e5b45065d3ac5269d29810fffae5201146d951b8`,
assembly/finalization
`ev_f20d56d975c43fb2f81535392e722376837ccf5bd4bb65eae81fd4724b981024`.
The external asset read verifies data availability and placement queries. It
does not demonstrate an original-equivalent initialized car or a driven race.
