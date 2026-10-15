# Driving recovery map

The [mechanical startup loaders](calculations/mechanical-component-loading.md)
now cover twenty-three component kinds in Python and C++, with original validation
and quality, including tire curves from eighteen external auxiliary records.
Thirty-eight selected actual Ford component calls match original execution in
sequence. The [ordinary unboosted engine finalizer](calculations/engine-curve-finalization.md)
matches eight stock engines in Python. Complete assembly and startup are still required before these
producers can initialize the recovered driving model.

This map identifies the original routines needed to replace the current driving
prototype. It records static observations and comparison targets; it does not
claim that the force model or a complete original driving tick has been recovered.
The executable is `mcity.exe`, x86, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Original disassembly, decompiler output and captures remain private.

## State of the implementation

The [connected drivetrain comparison](calculations/drivetrain-stages.md) now
executes all eight original engine driving children alongside recovered brakes,
loads, environment and tire forces in the Python harness. It passes 576 bounded
controller ticks across supplied-contact and recovered-support corpora. This
remains separate from the prototype viewer: authentic stock initialization,
terrain projection, remaining preparation/services, component implementation and
collision integration are still required. The five new drivetrain bodies also
have C++ ports matching 3,377 Python cases exactly. The independently verified
[startup gear-table producer](calculations/gear-binding.md) now also supplies
speed and inertia tables in two more integrated 288-tick comparisons. Full
native shared-state orchestration and original stock startup remain open.

The existing [motion calculations](calculations/vehicle-motion.md) cover bounded
active velocity, pose and wheel-point arithmetic. [Tire and suspension
parameters](calculations/tire-suspension.md) cover dimensions and component
interpretation. The [engine work](calculations/engine-dyno.md) recovers substantial
standalone curve calculations. These foundations are separate from the authored
120 Hz bicycle model in `client/driving.py`. Its acceleration, resistance,
steering limits and terrain-following placement must not become the specification
for the reconstructed original force solver.

## Scheduling and observed order

`0x567940` registers two callback lists, held at `0xaa4594` and `0xaa4590`.
`0x565d20` inserts callbacks in increasing numeric priority, placing a new entry
after existing entries of equal priority. The first list contains these vehicle
callbacks:

| Priority | Entry | Static role / research boundary |
| --- | --- | --- |
| 6 | `0x520c20` | Early object update; includes `0x51fc00` |
| 21 | `0x469010` | Pre-vehicle update, including per-vehicle interface dispatch |
| 30 | `0x53c140` | Branching vehicle motion and force update |
| 40 | `0x45abe0` | Object/terrain contact and collision path |
| 50 | `0x43d6e0` | Later vehicle update and interface dispatch |

The second list contains `0x520450` at priority 30, the active pose arithmetic
using `1/64`. Other callbacks occur between and around these entries. This table
does not omit them from a proposed implementation: it selects the driving seeds
whose complete dependencies must be traced next. Registration and sorting alone
do not establish frequency. The separately recovered [executor and driving
interleaving](scheduler.md) now show that the first list runs on even simulation
counters and the second on every selected subiteration. The selector chooses
zero, one or two subiterations; outer catch-up is capped at sixteen. Clock
production, mode producers and full outer flow remain incomplete. In particular,
`1/32`, `1/64` and support look-ahead `1/48` are arithmetic factors, not proof
of an independently measured frequency.

Sources: scheduler registration `ev_e4a36a338cd41b44e594b999c015a71ac9673355be94969ab1b18061807422ac`;
sorted insertion `ev_8dd8f9ab99394dc5275d0eb066ef7f3623130ac59e2efb27131b23c3c95c6744`;
pose `ev_ba52b567c332b0bb0222e7f95b8dcbabdad8868105dd9f1b02bed49b156ebdb1`.

Within the sufficiently supported branch of `0x53c140`, the static sequence
includes support queries and initial normal-load calculation, per-wheel surface
and grip processing, then these calls in order:

1. `0x53e030`, `0x540fd0`, `0x536480`, `0x536250`.
2. Body acceleration is transformed into local coordinates; its vertical local
   component is cleared before `0x53e680` and `0x53e980`.
3. `0x53e3d0`, engine update `0x545af0`, `0x538960`, tire response
   `0x53ecf0`, and `0x53e130`.
4. Predicate `0x55cfc0` controls calls to `0x5400b0` and `0x53fb30`.
   A per-wheel test can clear three force components. Global state controls
   `0x540520`; `0x540710` follows.
5. Body force and angular acceleration are combined/transformed. Angular
   velocity receives its `1/32` increment before linear update `0x540c30`.

This sequence is conditional. Separate inactive, low-support, tilted and global
mode branches follow different paths. Calls listed with addresses alone have
not been assigned definitive physical meanings. Some retained decompiler types
are visibly incorrect, so instruction-level checks are required for widths,
calling conventions and floating-point storage boundaries.
Source: `ev_6691a574a2c8313463ca5c8b1ffb2fa16c4305a4463d43be27ab00b2f64f2e84`.

Focused recovery corrects one earlier working label: `0x540fd0` handles control
and gear-input smoothing, so the controller action is `control_update`.
It is not an aerodynamic force stage. The body-resistance producer is
`0x536480`, followed by axle vertical-load adjustment at `0x536250`.
Their calculations and remaining environmental inputs are documented separately.
`0x54ebe0` prepares body-angle smoothing and transforms; `0x427da0` contributes
surface support disturbance. These identifications do not by themselves connect
the authentic input producers to a complete driving tick.

## Subsystem recovery targets

| Required behavior | Original seeds and bounded observation | Next comparison scenarios |
| --- | --- | --- |
| Contact/support and normal load | `0x53d320` predicts support; `0x53d920` branches on support count and attitude, redistributes four wheel loads and clamps them nonnegative | Every four-wheel support mask, attitude boundary, bank/slope, positive/negative vertical acceleration, repeated ticks |
| Acceleration-dependent load transfer | `0x53e680` adjusts the same four normal-load fields under attitude, acceleration and speed gates | Exact and adjacent gate values; acceleration/deceleration, left/right acceleration, clamp crossings, independent axle dimensions |
| Suspension-related load corrections | `0x53e980` changes wheel loads using support flags, body angles, component values and an engine-torque-dependent term | Supported/unsupported wheels, speed gate, component mode, torque sign, front/rear parameter changes |
| Tire forces and surfaces | `0x53ecf0` calls `0x53f630` and `0x53f830`; `0x53c140` reads surface classes and applies grip scaling before it | Zero/near-zero speed; forward/reverse; slip signs; unloaded wheel; surface classes; grip saturation; combined slip |
| Suspension curves and damping | `0x53acc0` calls `0x54a0e0`, `0x53f630` and `0x53f830`; `0x53b040` calls `0x538820` and `0x5399d0` | Curve knots/interpolation/extrapolation, compression/rebound, front/rear asymmetry, modified springs/shocks, repeated state carryover |
| Engine speed during driving | `0x545af0` selects mode-dependent paths, torque lookup `0x548f00` and RPM helper `0x546e70` | Startup/off modes, idle/redline, throttle boundaries, gear-state gates, positive/negative RPM corrections and rounding ties |
| Gears, clutch and differential | `0x546e70` reads gear-indexed state; `0x545af0` dispatches several helpers including `0x546330`, `0x5464c0` and `0x547120` | Neutral/reverse/forward gears, shifts under load, clutch engagement, one-wheel traction loss; identify actual component consumers before equations |
| Steering and brakes | Pre-update `0x469010` dispatches through the vehicle interface; force path includes `0x53e3d0`, `0x538960` and `0x53e130` | Trace input-to-field writes first; then full-lock/center, speed sensitivity, service/parking brakes, wheel lock and reverse braking |
| Body force/torque and aero | `0x540710` accumulates cross-product contributions and calls `0x540600`; active update includes `0x540520` | Single-wheel forces, offset center of mass, pure drag/lift, sign reversals, no-contact gravity and rotated body |
| Terrain/object collision response | `0x45abe0` invokes `0x45a320`, `0x459150`, `0x458530` and other conditional paths; `0x45a320` includes terrain-plane and impulse-related calls | Resting plane, edge contact, wall/head-on/oblique impacts, vehicle pairs, tunnelling, recovery and damage branches |
| Integrated tick ownership | Sorted lists plus `0x53c140`, `0x45abe0`, `0x520450` | Recover executor; capture exact callback sequence, state before/after each stage, focus/pause/catch-up and mode transitions |

The filenames of private research records are working labels. In particular,
`189-drivetrain-step` and `190-wheel-torque-step` do not establish gearbox or
wheel-spin integration: their retained routines primarily modify the four
normal-load fields. They belong in the load-transfer investigation until their
inputs and units are independently confirmed.

## Evidence index for focused follow-up

| Entry | Evidence ID |
| --- | --- |
| `0x469010` | `ev_93a549dde7dde6d9b02b5ce7c7d702fd09ee6023ac274791e5b94d33d2cd79e9` |
| `0x53d320` | `ev_f04dec3c392ad24344e59e34d5c69e17e64ee1532b5945b4ef2c74bb0683da4b` |
| `0x53d920` | `ev_3ce59f9fae6e5945433fe36e417989cccb95f3593354d62e894b55e00e227174` |
| `0x53e680` | `ev_f3e335bc28f50f40e5da374c23b5d94606e2e2f2aff28eac5b1242ecbd0d206c` |
| `0x53e980` | `ev_901762dd68045061e4da4cb117551ab19ce34b5193a1808fcfa29c70ef91fc3b` |
| `0x53e3d0` | `ev_7ff157fe7a67d366a052b34b7128caa17c1a2f2b1e2637d7eb4ded64a8ade087` |
| `0x53ecf0` | `ev_6dbd3a74a88796f6cde2cfb7eb3eae4a3137cbabc2cb867a16c1c5924893a8d6` |
| `0x53acc0` | `ev_40cf4b087f0020daf8f2caccb7949d76d8d96e494e655d934ffc84e43a343428` |
| `0x53b040` | `ev_8bafb61e22c721710b8ca35c5602ebd4becb9d401fc6287d98869789b67ff131` |
| `0x54a0e0` | `ev_2698d50ba5d30310e15865800cf33e8b7f249bd27fba36ecdd2a6d56fa2bb8ed` |
| `0x545af0` | `ev_f4138fe586f7a644826c3fed0bf4ac2ff952ab9063efe9cdcc51b1623111253b` |
| `0x546e70` | `ev_3c8099ab7007ea9a2eb5f2aaa8d0f9810ddcb1d07efdde478a912e3a8402e7d7` |
| `0x540710` | `ev_562052f2f87aabaa33b332a4e182eba57b808636146ddf65da5b6e41c51528ab` |
| `0x540c30` | `ev_07e93f4c881dfdfb041e72a77c4da190278fe07871d1fbb763170843858794c2` |
| `0x45abe0` | `ev_2af27d45965b5ef952cbdc5179b0aa9347656a134bcd84101f714f1d3ac67dc3` |
| `0x45a320` | `ev_c373f4410de6747afe9deb8653fe7060d949e66e7a138ba5e9f2b03f5711b003` |

## Integration gate

The [vehicle controller](calculations/vehicle-update.md) now reproduces all six
dispatch paths and controller-owned numeric changes, including per-wheel force
clearing and motion accumulation. Its mandatory child executor keeps missing
behavior explicit. A 2,607-case original comparison includes actual connected
linear-update instructions and supplied child mutations. This does not supply
authentic contact/engine/input producers or complete child-stage integration.

The [response-table consumers](calculations/tire-response-curves.md),
[wheel resistance contribution](calculations/rolling-resistance.md) and
[acceleration-driven load correction](calculations/load-transfer.md) now have
original-function comparisons and C++ ports. These bounded steps do not recover
their surrounding input producers or complete force tick.
The [initial normal loads](calculations/normal-load.md),
[wheel speed projection](calculations/wheel-speed-projection.md) and
[suspension load correction](calculations/suspension-load-correction.md) are also
verified and ported. The [shared-state sequence](wheel-load-sequence.md) checks
load handoff through three stages, while retaining explicit caller exclusions.
The [speed-dependent steering input helper](calculations/steering-response.md)
also has complete original-function comparisons and a native port. The
[combined tire update](calculations/tire-update.md) now connects input shaping,
front/rear steering geometry, slip, response curves and force gates. Its
[per-wheel predicate](calculations/vehicle-gate.md) has a bounded original
comparison, while the virtual observation producer and counter scheduling
remain external. Full vehicle integration and authentic-car traces remain open.

Parallel recovery now also supplies [driving RPM and a coupling tail](calculations/driving-engine-rpm.md),
[wheel-force/spin correction](calculations/wheel-force-correction.md),
[brake thermal initialization](calculations/brake-thermal.md),
[complete numeric brake forces](calculations/brake-forces.md),
[wheel-spin integration](calculations/wheel-spin.md),
[combined-slip force limiting](calculations/combined-slip.md),
[body moments and force orientation](calculations/body-moments.md), and
[collision calculation helpers](calculations/collision-helpers.md).
Complete child-stage integration, authentic producers, contact creation, brake wear and
event delivery and integrated velocity/collision traces remain open. The
native runtime includes these verified consumers without replacing the playable
prototype with an incomplete mixture of recovered and guessed forces.
The [shared-state force sequence](driving-force-sequence.md) now checks tire,
spin correction, spin integration, combined-slip limiting, orientation and
body-moment handoff across repeated calls.
Its excluded caller branches remain visible; it is not a recovered full tick.

The [connected environment](calculations/wind-drafting.md) now runs actual
density, weather, wind and drafting producers inside original body resistance.
Its shared-owner comparison checks peer wake writes as well as body forces.
[Control smoothing](calculations/control-update.md) and [engine condition/thermal
links](calculations/drivetrain-links.md) have complete numeric bodies, with their
remaining remote/gear and damage/effect interfaces explicitly supplied.

## Immediate playable milestone

Load production, control smoothing and body/environment now feed the same
[controller force pipeline](driving-pipeline.md), with actual original support
prediction included in its larger comparison. Terrain projection, full engine
and brake handoffs, preparation and authentic initialization remain open.
The separate [engine pipeline](calculations/engine-pipeline.md) connects torque
and thermal calculations across persistent calls; it still requires its actual
clutch/gear/wheel-drive producers. [Owner mass/inertia binding](calculations/owner-binding.md)
is recovered from explicit finalized configuration/model inputs, while creation
of those finalized inputs remains a startup blocker.

The [typed driving pipeline](driving-pipeline.md) now connects six recovered
force stages to the controller and binds support results to its branch/contact
state. The [stock startup audit](calculations/stock-driving-startup.md) reads the
actual vehicle 101/Drag inputs and identifies missing assembled configuration
instead of substituting research defaults. Complete authentic startup remains
open; the pipeline is not yet selected by the playable client.

The [body configuration initializer](calculations/body-configuration.md) now
supplies actual catalogue wheelbase, tracks, body-base mass and clearance
references. These are reported separately from mesh measurements and final
assembled-car values. Original owner binding and remaining component aggregation
still need recovery.

The complete [engine torque update](calculations/engine-torque-update.md) now
recovers engine braking, condition deductions, nonlinear throttle gain, coupling,
RPM update and ordered damage/effect requests. Boost and pulse generation,
catalogue-derived setup and actual component effects remain explicit boundaries.
The [support predictor](calculations/support-prediction.md) reproduces original
transform precision and contact arithmetic, retaining terrain projection as an
explicit required service rather than using prototype height-selection rules.

Prioritize one stock car on the original Drag track through the recovered
simulation. Passing more isolated routines alone does not close this milestone.
The Python engine bridge now connects recovered torque, condition and RPM bodies
to the integrated controls/load/environment/force controller; 288 original ticks
check shared publication, carryover and nested ordering. Brakes now join the Python controller
comparison with original thermal/force bodies, selected-gear inertia and ordered
effects; see [integration scope and numeric differences](driving-pipeline.md#brakes-bound-into-the-vehicle-tick).
Engine setup/control, clutch/engagement, wheel-drive distribution, terrain
projection and remaining preparation are still supplied. Replace those bodies
and connect authentic catalogue/geometry inputs to the shared car state before
treating this as a driving implementation. Preserve observed stage order,
scheduler counters and repeated state carryover.
Recover missing child behavior along this path; do not fill it with the bicycle
model's handling constants or silently accept default subsystem records.

The headless integrated run must expose its remaining supplied observations and
match original acceleration/coast/braking/cornering state before the rendered
client selects it. Reuse the existing decoded-track view and controls for the
testable milestone. Complete collisions, other car configurations, race rules,
both-platform gameplay and online racing remain later completion requirements.

First compare isolated routines against bounded original execution, recording
every replaced call, original input/output image, rounding mode, and tolerance.
Then compare connected stages with the original update sequence and authentic
assembled-car inputs. Use repeated ticks to catch state carryover that single
calls cannot establish. Finally record original-client acceleration, coast,
braking, steady cornering, skid, airborne and collision scenarios for stock and
modified cars. Until those comparisons pass, keep the prototype visibly separate
and leave faithful driving incomplete in the [recovery ledger](recovery-ledger.md).
