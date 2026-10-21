# Model preparation dependencies

This package translates original local-space part half-extents (`0x4c4050`),
three-stream part scaling (`0x4c42d0`), and secondary-model alignment after
selection of its reference node (`0x52bc60`). Addresses apply only to main
executable SHA256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

The implementation uses complete FCE byte images. The existing decoded model
does not preserve dummy positions and every stream mutated by the original.
The image is caller-owned; these functions allocate no original objects, acquire
no model ownership, and infer no reference counting or destruction policy.
Finite vectors, bounded tables, terminated names and valid selected parts define
the supported input domain. Malformed images raise errors rather than emulate
the original out-of-bounds memory behavior.

## Observed shared layouts

| Object | Offset | Meaning used by this call chain |
|---|---|---|
| Assembly owner | `0x19c` | Head of component/model linked list |
| Assembly owner | `0x40` | Component-node count incremented by `0x52add0` |
| Assembly owner | `0x214` | Secondary model pointer |
| Assembly owner | `0x21c` | Head of selected render-part linked list |
| Assembly owner | `0x22c` | Flags; bit `0x40` suppresses later type16/17/18 lift |
| List node | `0x00` / `0x04` | Next node / model pointer |
| List node | `0x0c` | Signed 16-bit part index |
| List node | `0x10` | Flags; bit `0x40` selects mirrored bounds |
| List node | `0x14` / `0x18` | Type selector / wheel-position selector |
| Component node | `0x3c` / `0x40` / `0x44` | Three float size fields used by tire preparation |
| Component node | `0x338` | Class selector |
| FCE image | `0x58` / `0x5c` | Dummy count / contiguous xyz dummy origins |
| FCE image | `0x11c` / `0x120` | Part count / contiguous xyz part origins |
| FCE image | `0x420` / `0x520` | Per-part first-vertex index / vertex count |
| FCE image | `0xe28` | Part names; 64-byte entries |
| FCE image | `0x14`, `0x34`, `0x2c` | Offsets of the three scaled vector streams, relative to `0x2038` |

The list nodes and FCE images remain separate objects. Multiple nodes can refer
to one image; future assembly adapters must preserve this aliasing rather than
copy each node's model. The containing owner does not establish ownership or
lifetimes through these functions alone.

`client/model_owner.py:selected_render_head` translates the small selection
primitive `0x52d070`: starting at the requested slot, scan owner render-list
heads at `+0x21c` downward through slot zero and return the first non-null head.
The direct original comparison covers all 16 occupancy patterns of the four
slots at all four limits (64 calls). This selects an existing render list; it
does not produce component/model nodes at owner `+0x19c` or render lists at
`+0x21c`.

`client/model_owner.py:build_component_node_list` translates the successful
path of `0x52add0` for an existing owner with an empty component-list head.
For each supplied 0x984-byte `tPartInfo` template, it calls the original lookup
with the class/attachment pair, copies the full template, stores that result
at `+0x11c`, applies bounds, unit-scale, zero and next-pointer overrides, and
prepends the node to the owner list. Three complete calls (six nodes) match
original memory exactly; the allocator and `0x528a70` lookup are stubbed with
recorded return values. Owner creation, allocation failure cleanup, actual VIV
model loading, the unported string/model-source fields from `0x52c2e0`, and the
earlier DBAPT stock/config loading path remain outside this adapter. The
`0x52c550` selector and paired-attachment order are separately translated in
`client/mechanical_parts.py`; they do not produce complete address-bearing
`tPartInfo` nodes by themselves.

The composed `build_stock_component_node_list` path now joins these stages for
already-loaded DBAPT slots: `0x52c550` pairing, complete `0x52c2e0` mechanical
records (including model/display strings), then successful `0x52add0` owner
nodes. The original comparison runs the installed Ford stock vehicle 101
through `0x52c550`, `0x52c2e0`, and `0x52add0`: 45 source slots become 57
complete mechanical records and owner nodes with zero byte differences. The
worker's missing-driver fallback then executes original `0x52c190`, producing
the 58th exact node with the `Driver` name and owner head/count update. The
allocator and class/attachment resource lookup are deterministic stubs; owner
construction starts from an existing empty owner. Run
`tools/verify_stock_component_owner.py <mcity.exe> --game-root <game-root>`.
DBAPT acquisition, owner initialization, live model-file loading and later
geometry/render preparation remain open.

`complete_ready_stock_owner_job` now translates the deterministic successful
result tail of stock-owner worker `0x52c790`. Two original worker executions
on installed vehicle 101 cover the unmatched `-DBAPT_kVehicle not found-`
label and the matched vehicle-name/ID branch; each compares the complete owner
image and 58 linked component nodes with zero byte differences. The calls to
`0x52c6b0`, `0x52c550`, `0x52c2e0`, `0x52add0`, `0x52c190`, `0x530a90`,
`0x699330`, and `0x52ca30` run in the original. The asynchronous completion
query, thread-ID import, pool allocator, class/attachment lookup and release
handles are controlled bridges; live worker scheduling and custom/owned-vehicle
processing remain open. The preceding `poll_owner_job_result` gate covers
immediate states 0/98 and pending-to-terminal transitions with matching and
nonmatching pump threads. Four original `0x52c790` calls confirm 10 ms sleeps,
conditional callback pumping, zero returns and unchanged owner bytes. Reproduce
those with `tools/verify_stock_owner_worker_poll.py <mcity.exe>`. Reproduce the
pre-expansion rejection gates with `admit_stock_owner_job` and
`tools/verify_stock_owner_worker_failures.py <mcity.exe>`: three original calls
cover invalid completion status, zero slots and scratch-allocation failure.
Only the allocation-failure branch releases the completion result; all three
return zero without changing owner memory. Reproduce the
ready comparisons with
`tools/verify_stock_owner_worker.py <mcity.exe> --game-root <game-root>` and
add `--exercise-selected-slot` for the matched-label branch.

## Complete translated primitives

`model_part_half_extents` / Python `part_half_extents` scans the selected part's
first vector stream without adding the part origin. Each result is
`float32(abs(maximum - minimum) * 0.5)`. Invalid indices and zero-vertex parts
produce no result. Other parts and all model bytes remain unchanged.

`model_scale_part_streams` / Python `scale_part_streams` multiplies selected
xyz values by the supplied axis scales in stream order `0x14`, `0x34`, `0x2c`.
Each multiplication stores float32. It does not normalize vectors, change part
origins, or update dummies. Aliased streams are visited repeatedly; three
identical stream offsets apply the scale three times. The stream semantics
beyond these observed memory operations are not assumed by this API.

`model_align_secondary` / Python `align_secondary_model` accepts the secondary
image and an already-selected reference image/part. The original wrapper first
checks owner `0x214`, then takes the first type `0x11` node in the `0x21c` list.
It requires that selected node's model pointer and signed part index be valid.
The translation receives that selection explicitly and checks its bounds.

The first secondary part whose NUL-terminated name contains case-sensitive
substring `_W` supplies the source origin. Let `R` be the reference origin and
`S` that source origin:

```
D.x = float32(R.x - S.x)
D.y = float32(R.y - S.y)
D.z = float32(R.z - S.z)
D.y = float32(D.y + 0.05000000074505806)
```

The stored vector is then added to every secondary part origin and dummy origin,
with float32 stores. Geometry streams and all other bytes remain unchanged.
The delta stores are visible in instructions `0x52bd5b..0x52bd84`; simplifying
the pseudocode into one unrounded expression would change behavior. Original
`0x52bc60` returns void; the authored adapter returns whether alignment occurred.

## Connected startup contract and remaining gates

Observed `0x52be40` order:

1. Save the selected-part list head from owner `0x21c`.
2. Run tire preparation `0x52b950` for selectors **1, 2, 4, 3**, then suspension
   preparation `0x52b7c0`.
3. Union valid nonempty selected-part bounds through real `0x4c3e50`, honoring
   each node's mirror flag.
4. Calculate negative center and half-extents, then translate every part and
   dummy origin in each model reached through owner `0x19c`.
5. Run secondary alignment `0x52bc60`.
6. Unless owner flag `0x40` is set, lift y of selected part origins with node
   types `0x10`, `0x11`, `0x12` by stored `0.05f`.
7. Publish the union half-extents.

The apparent head search in the export starts at index0 and immediately exits
after a failed check; it does not justify searching other owner head slots.

`prepare_tire_models` translates `0x52b950` over an explicit typed component/model
list. It selects the first tire component at a requested position, computes its
float32 tire dimensions with the original x87 radius expression, finds the first
nonempty `:PH` template, then adjusts and scales matching tire/rim/brake model
records. The class selectors are `0x1adb1`, `0x186a1` and `0x1d4c1`. The width
helper `0x53bf10` subtracts stored float `0.23000000417232513`; radius helper
`0x53bf20` stores `max(float32(radius - 0.3700000047683716), 0)` before returning.

`tools.verify_model_group_centering --tire-cases 256` compares 256 complete
original `0x52b950` executions for one tire component/model, including status and
all three mutated FCE streams, bit-for-bit. Selection misses, multiple attached
components, and full stock wheel graphs remain outside that comparison. Do not
promote this to complete component/model loading.

`prepare_rear_suspension_model` translates `0x52b7c0` for an explicit component
and model list. The original selects a class `0x1adb1` wheel at position3,
falling back to4, plus the first class `0x3e9` component. It looks up exact
case-sensitive `:PHrearsusp` and `:PHtire` names with `0x4c5ca0`, uses the
tire part's absolute x origin and suspension x half-extent to scale suspension
x, then copies tire y/z origin and stores suspension x=0. A seeded oracle
compares all FCE bytes and the return value for 128 calls, covering both wheel
position branches. The complete upstream component/model producer, other model
graph shapes, and stock owner startup remain integration work.

## Prepared model-group centering (`0x52be40`)

`client/model_group_centering.py` translates the centering tail after component
placement: it unions selected nonempty part bounds, recenters part and dummy
origins in model-list order, invokes the recovered secondary-alignment adapter
when its selected reference is supplied, applies the conditional 5 cm mount lift,
and returns the resulting half-extents. Model indices preserve component-node
aliases to shared FCE images. This operation accepts an explicitly prepared
graph; it does not construct or own component nodes, load attached models, or
substitute tire/suspension placement.

The same original-entry oracle now composes stock body flags and the recovered
`0x52d710` body collector with `0x52be40`. For vehicles 101–108 it builds the
selected body surface list from installed catalogue/FCE data, carries each
record's part, flags and type into the native linked-node image, then compares
the complete mutated body image and published extents with the Python graph
operation. All eight match byte-for-byte. The verifier still constructs the
component and selected-node lists; it does not prove the original owner-list
producer or include attached component archives. Reproduce with
`python -m tools.verify_model_group_centering <mcity.exe> --game <game-root> --stock-body-collector`.

`tools/verify_model_group_centering.py` executes the original entry `0x52be40`
for 256 seeded single-node cases, checking the entire FCE image and stored
extents bit-for-bit. `prepare_vehicle_model_group` composes the original order:
tire preparation at selectors 1, 2, 4, 3; rear-suspension placement; then the
bounds/centering tail. The same runner compares this full entry path against
128 seeded three-model graphs, including the complete FCE images and published
extents. It also compares all model bytes and extents for the eight installed
stock vehicles 101–108 using their actual body, tire and suspension FCE files
and catalogue tire dimensions. That stock run uses an explicitly constructed
one-wheel component graph; it does not prove the original owner/list builder
produces that graph or cover four-corner aliases. The primitive verifier checks
original `0x4c4050` in both mirror modes. The eight stock collector cases have
no selected mirror-bit records, so mirrored bounds remain tested only by the
synthetic corpus.
Multi-wheel aliasing, mirrored bounds through the enclosing function, selected
mount lift through the enclosing function, secondary-alignment integration and
original owner model-list construction remain unverified. This does not
complete owner model assembly or driving geometry.

Evidence: model-group entry
`ev_05865089981494cc62e66b6b403e1acfef1769db893294fcc7bb4927f89a29ed`;
selected-part bounds
`ev_d7d24f4e6b390a76ff3f4edfa09189c93f9309ecf9f9d0e5f743f6a368ccaf91`;
secondary alignment
`ev_dbb8bb8c451d3072a60915d8a99e2c36ad0b8c8f37bea7ede24bd1adcef9157f`.

## Reproduction

```
python -m unittest tests.test_model_preparation
python -m tools.model_preparation_oracle "<original>/mcity.exe"
python -m tools.native_model_preparation_compare "<build>/mco_model_preparation_compare.exe"
```

The original oracle executes **106 calls**: 40 half-extents, 40 scale operations,
26 secondary alignments. It checks status/output for half-extents and the entire
image, including untouched sentinels, for mutations. Inputs include empty and
invalid part indices, separate and aliased streams, case-sensitive/name-substring
selection, multiple matching parts, nonzero dummy origins, and missing-secondary
or missing-selected-node exits. The original CRT substring helper executes;
there are no replaced child functions. CPU-only bounded execution is not an
original-client runtime trace. Native comparisons use the same authored corpus
and require exact output bytes.

Retained REA dossiers: `0x4c4050`
`ev_d7d24f4e6b390a76ff3f4edfa09189c93f9309ecf9f9d0e5f743f6a368ccaf91`,
`0x4c42d0`
`ev_5e50dc0766a99b7f87c8ce67f37388aae53a3113f010bc36b5e30fc1a4bbc5aa`,
and `0x52bc60`
`ev_dbb8bb8c451d3072a60915d8a99e2c36ad0b8c8f37bea7ede24bd1adcef9157f`.

## Component render-list lookup

The owner-node selector is now represented separately as
`select_component_node` in Python and C++. It scans requested LOD down to
high-detail, and within each LOD scans owner-node order, matching the 12-slot
native component-class table (including the repeated `R` class slot). The
winning model handle, part index and flags are retained in the render record;
the exported index is the newly appended render-record index, not the owner
node index. `tools/verify_component_node_selection.py` compares all 12 slots,
duplicate-class resolution, priority ordering, records, and miss cases against
`0x52e670` (16 synthetic calls). This extends coverage beyond the four wheel
prefixes, but does not reconstruct how the game builds or owns the complete
component-node list.

## Final render-list ordering

`0x52dd70` is the owner-level render-list producer, not just a sort routine. It
finds the owner component node whose type is `0x4e21`, clamps the requested
LOD to 3, clears owner flag `0x10000` above LOD 2, invokes the body collector
`0x52d710` and component collector `0x52df00`, allocates and copies the
nine-word records, sorts descending by word 5, then replaces each record's word
0 with the next native record address and terminates the final link with null.
The strict adjacent-swap comparison preserves collector order for equal keys.
This is observed in fresh REA Evidence
`ev_56cf0a8a5f38eb63af02e712140904ba0c5270365e28b81d80d44b74c3297385`.

`client/render_list.py` and `native/src/render_list.cpp` implement the portable
sorting/linking subpass, with links represented as record indices. The portable
code still does not own the native owner lookup, full collectors, allocation
lifetime or pointer values. `tools/verify_owner_render_list.py` compares 30
body-only original owner calls across five LOD values and six body flag
profiles, including all 297 output records. A 31st call exercises a nested
generic component graph through `0x52df00`; both mutated component FCE images
and the final two linked records match. Each comparison intercepts only the
allocator call at `0x52de2c`; owner lookup, LOD/flag normalization, collection,
copy, sort and relink execute in the original. The direct execution exposed
the descending native order and corrected both portable ports. A later
installed-stock fixture exercises available component models and special
branches; allocator/resource lifetime and vertex-stream runtime layout remain
open.

`collect_render_group` now translates the selection core of `0x52db70` in both
Python and C++. For each LOD from the requested value down to high detail, it
searches linked-model order and each model's part order for an exact `:H`, `:M`,
`:S`, or `:T` name. It writes the chosen model handle, 16-bit part index, flags,
and mesh type into a nine-word render record. The original retains the
*requested* LOD bit in the record after a lower-detail fallback; this was
confirmed in direct execution rather than inferred from the returned part.

`tools/verify_render_group.py` compares eight bounded synthetic calls against
the original `0x52db70`, covering fallback order, model order, flags, exact-name
misses and record contents. The portable model handle is an index, not a native
pointer, and these calls do not recover the owner graph. REA Evidence:
`ev_1fb8609a1b3c76d7168b0365a30754cce70648c463e465e3f5b054bfdae26597`.

The ordered `0x52d710` body collector is also implemented as
`collect_body_render_records`. It emits base body/headlight records, conditionally
adds interior/dashlight/steering, then follows the original flag-driven body
group order and record types. Six direct original executions compare 61 records
across stock, roof, convertible, chopped, cage, skirt, mirror and LOD profiles;
`tools/verify_body_render_groups.py` checks the selected parts, flags, types,
order, and temporary linked-record addresses. The native implementation has
unit coverage for representative ordering. `collect_component_render_graph`
now composes generic accessories, driver/head, wheel, rear-suspension and the
engine gate, and the stock fixture connects these records to original
`0x52dd70`. Other special suffixes and non-stock/custom assemblies remain
incomplete.

The stock preview now uses the bounded attachment-name behavior recovered from
`0x52df00` and `0x52e670`: wheel markers select the `LF`, `RF`, `LR`, or `RR`
component, then the component image is searched for the exact `:PHtire` or
`:PHhubcap` part. The helper tries the selected `:PH`…`:PT` option range in
descending order and emits the original mirror and option flags in its render
record. Four planted calls to `0x52e670` match the original part index, model
pointer, list count and record fields, including a missing-name case.

When stock tire dimensions are available from the catalogue, each corner's
tire and rim FCE images are prepared with `0x52b950` before rendering. The
rear `:PHrearsusp` mesh is scaled from the prepared left-rear tire and placed
at the body's `:PPrearsusp` marker. The verifier compares all tire+rim image
bytes and statuses for 32 stock vehicle/corner pairs (vehicles 101–108, four
corners each); the full body/tire/suspension preparation call also matches for
all eight stock vehicles in its documented synthetic three-node graph. The
installed owner render-list comparison includes the actual four tire and four
rim nodes per stock vehicle, though the full upstream preparation/resource
lifecycle is not yet represented as one production path.

For stock cars the preview places the selected `ENGINE.viv` `:PHengine` part at
the body's `:PPengine` origin, then follows available nested `:PPmanifold`,
`:PPcarb`, and `:PPaircleaner` markers into the stock `MANIDUAL`, `CARBSING`,
and air-cleaner archives. Child origins use parent-part-relative marker
coordinates. The `:PPvalve` marker resolves to owner class 1500001 according
to the native startup dispatch table; the stock vehicle catalogues omit that
class, though global `valvefh.viv` and `valvev8.viv` archives exist. The
preview attaches a selected valve-cover node if present rather than confusing
it with the mechanical `valvetrn` part. The composed collector follows stock
engine child markers and matches installed owner records for vehicles 101–108.
Custom configurations, all valve/engine variants, runtime vertex layout, and
full resource-lifetime equivalence remain open.

The startup class-to-archive dispatch comes from `0x52d1e0`; its retained
REA Evidence is `ev_d2847525e050b325e50bedd4822863cd40b05602ffe41ae43108014c84820157`.

This comparison does not recover every custom owner-node list, component class
index, body accessory, or recursive/nested submodel. See
`tools/verify_component_render_lookup.py` and `client/scene.py`. Retained
decompilation Evidence for the helper is
`ev_6f1766a884a654cabf1fc986396ed55a747bbe78422f7731a54303f52c41f024`.

## Driver model selection

The special rear-suspension marker branch of `0x52df00` is now represented by
`attach_rear_suspension` in Python and C++. It selects the requested `:PH` to
`:PT` `rearsusp` part, places its origin at `:PPrearsusp`, and emits the native
record flags (`1 << requested_lod | 0x80`) and type `0x0f`. Five direct original
calls verify all four LODs plus the absent-part path; the verifier checks the
mutated FCE origin and all relevant record fields. This is one special branch,
not a translation of the recursive owner/accessory collector. See
`tools/verify_rear_suspension_attachment.py` and REA Evidence
`ev_d6dec482edef7d00b25817721f9a3ccaafe52ca02d8206f3cd0daf6c01f435b0`.

The ordinary generic `:PP` marker branch is also translated as
`attach_component_marker` in Python and C++. Four direct original calls cover
left/right class flags, the engine marker gate, option fallback, LOD-zero vertex
transformation, selected-part origin replacement, and nested `:PP` marker
rebasing. At LOD zero,
all model vertices are translated relative to the selected part origin, with X
reflection for `R*` classes; other LODs retain the vertex stream while still
moving the selected part origin. These checks use synthetic one-node models and
do not cover class-list search across real owner assemblies or recursive child
selection. See `tools/verify_generic_component_attachment.py`.

`collect_component_render_graph` now composes class-table lookup, generic
marker attachment and LOD-zero recursive traversal for an explicit native-order
component-node snapshot. It carries each mutated model forward so nested
markers observe the updated origins and vertex stream. The `0x52dd70` oracle
fixture now exercises a two-level L/R graph through the original
`0x52df00` recursion and final owner-list sort/link path; both complete
component FCE images and both output records match. This verifies that graph
shape. Separate installed-stock comparisons now cover owner model resolution
and records for catalogue vehicles 101–108; complete runtime model conversion
and allocator/resource ownership remain separate.
Reproduce with `python -m tools.verify_owner_render_list <mcity.exe>`.

The special driver marker is also composed into `collect_component_render_graph`
for explicit owner nodes tagged with component type `0x80e9`. It emits the
`:PHdriver` and `:PHdriverhead` records, places the driver at `:PPdriver`, and
places the head using the native head-minus-driver offset. A regression test
covers record types and transformed origins. The installed-stock fixture
`tools/verify_stock_owner_render_list.py` resolves the catalogue's absolute VIV
paths relative to the game root and derives visibility flags from catalogue
part identities. It loads the stock body and every available component FCE
from the native linked-list snapshot, then compares final `0x52dd70` records,
links, and selected part origins for all eight installed stock vehicles
(IDs 101–108) at requested LODs 0–4. All 837 records and links and 3,950 part
origins match. Per-LOD record counts are 25/22 for vehicle 101, 23/20 for 102,
22/19 for 103–105, and 21/18 for 106–108 (LOD 0–2 / LOD 3–4). The fixture
replaces only allocation and resource handles; archive path resolution uses
the installed files. Native vertex storage is an expanded runtime model layout,
so complete vertex-stream mutation equivalence is still open. Use `--all-lods`
to repeat all five comparisons for one stock vehicle.

The composed graph collector also routes `:PPrearsusp` to the verified special
branch and carries the owner's `0x10000` gate into generic `:PPengine`
selection. It clears that gate for requested LODs above 2, matching the owner
collector's normalization. Unit checks cover the enabled/disabled engine case
and rear-suspension record/origin; direct original comparisons remain
`tools/verify_generic_component_attachment.py` and
`tools/verify_rear_suspension_attachment.py`. The installed stock comparison
also exercises the resolved tire, rim, engine, and suspension model nodes.

The graph collector now also composes the special `:PPLFwheel`, `:PPRFwheel`,
`:PPLRwheel`, and `:PPRRwheel` branches. It selects `:PH`…`:PT` tire and
hubcap meshes independently, places both origins at the wheel marker, and
emits the corner-specific mesh types and right-side flag. The direct
`tools/verify_wheel_attachment.py` comparison passes 16 original `0x52df00`
calls covering all four corners and LODs 0–3 (32 records, origins and links).
It uses synthetic FCEs; actual per-vehicle tire/rim owner-node integration
remains unverified.

Startup `0x52d1e0` reads the driver selector byte at owner offset `0x17c` and
indexes a 33-row table with nine pointers per row. The first pointer in each
row selects a `DRIVER*.viv` archive; `client/scene.py` retains the observed
index-to-filename mapping and the preview exposes it as `--driver-variant`
(indices 0–32, default 0). The original `0x52df00` branch selects both
`:PHdriver` and `:PHdriverhead`, places the driver at `:PPdriver`, and offsets
the head from the driver's original part origin. The original routine matches
all 33 installed driver archives in `tools/verify_driver_attachment.py`,
including complete modified FCE bytes and both render records. The composed
`stock_scene` path now rounds the head-minus-driver offset and subsequent
marker addition separately to float32, matching the native stores; a
cancellation-sensitive regression test checks that behavior. The mapping
Evidence is `ev_2bb1a50f22aa110fcae0ad6807e61ad32427d0874e8b798d720fcdabd5078a9d`;
the startup routine dossier is
`ev_d2847525e050b325e50bedd4822863cd40b05602ffe41ae43108014c84820157`.
The account/profile value feeding the original selector is still unknown, so
the preview's default index does not claim a specific user's driver choice.
