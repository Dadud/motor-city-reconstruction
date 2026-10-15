# Connecting the recovered driving stages

`client.driving_pipeline.DrivingForces` is a stateful child executor for
`client.vehicle_update.update_vehicle`. It binds tire forces, wheel correction,
spin integration, combined-slip limiting, force orientation and body moments to
the controller's current typed vehicle state. The controller selects branches,
clears unsupported wheel forces and accumulates motion in its recovered order.

The executor reads shared values immediately before each child call. It retains
wheel fields absent from the controller view, including spin adjustment, slip
ratio, secondary response and support correction, across successive calls.
Controller mass and the configuration mass used by moments remain distinct.
Spin phase, contact, normal load, surface coefficients and oriented forces are
never restored from a stale template after another stage changes them.

Construct `ForceInputs` with explicit tire, spin and moment records plus current
control and orientation inputs. Supply two required callbacks:

- `external(call, controller, force_inputs)` executes every other child and
  returns required observations. It can update records held by `force_inputs`
  when control, engine or preparation stages produce new values.
- `effects(kind, events, controller, force_inputs)` consumes ordered component
  events after spin or slip limiting. Mutations are visible to the next stage.

Keep the executor instance across ticks. Call `update_vehicle(previous.state,
executor)` for the next controller call. Its result owns a copied controller
state; the executor retains its side records. This is a single-vehicle,
sequential interface, not a concurrent or rollback simulation API.

`client.driving_support.DrivingSupport` can wrap the external callback. It binds
the [support predictor](calculations/support-prediction.md) to current body
velocity, transform, contact reference and fallback surface, then writes contact,
surface descriptor, support difference and support count back into the same
controller state. Position, local support points and terrain records remain in
its explicit prediction record. Motion/preparation producers must update that
record; original terrain projection is a required callback.

The integration tests exercise controller branch changes from projection
results, repeated support/wheel state, independent gates, clearing before moment
accumulation, immediate component mutations and distinct mass fields. These
tests do not recover missing producers or prove stock-car handling. The
[stock startup audit](calculations/stock-driving-startup.md) records the actual
remaining asset-to-simulation bindings. The playable client still uses the
labelled prototype until original assembled inputs and connected behavior pass
the driving acceptance scenarios.

## Original controller comparison

Run the bounded comparison against the separately supplied verified executable:

```powershell
.venv/Scripts/python.exe -m tools.driving_pipeline_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

This executes original controller `0x53c140` with actual original tire,
wheel-correction, wheel-spin, combined-slip, orientation and moment functions,
plus original linear update `0x540c30`. The Python controller uses the stateful
force executor for two consecutive calls. The corpus covers 144 scenarios and
288 controller ticks, exercising three speeds, three support masks, both
independent controller gates, both orientation modes and wheel-force clearing.
It executes 1,296 recovered force calls and 20 component-mutation ticks.

Maximum owner numeric error is **0.000244140625** and maximum component argument
error is **7.275957614183426e-12**. These pass recorded tolerances of
`max(0.0005, abs(original) * 4e-7)` for owner floats and
`max(3e-10, abs(original) * 4e-7)` for effect arguments. Ordered controller calls,
query arguments, component receivers, axle operations and event order match.
Remaining owner bytes match exactly and configuration buffers remain unchanged.
Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
This is numerical agreement within recorded tolerances, not a bit-identical
claim.

Other children and mode/component delivery remain supplied. The corpus uses
authored input records, not original stock initialization. In particular, the
component mutation changes wheel 0, which has already been processed, and
checks its force handoff to later stages. The Python executor delivers collected
events after the entire originating stage; the original calls components inside
its wheel loop. This comparison does **not** verify a component callback that
changes an unprocessed wheel or another value consumed later in that same loop.
Recovering that effect behavior and its interleaving remains required before
claiming full original-equivalent component delivery or stock driving.

Adding `--actual-support` executes original support prediction and its scalar
transforms inside the same controller. The terrain projection remains supplied
with exact ordered point/context/record checks. This second corpus passes 288
ticks: 192 supported and 96 low-support branches, 1,152 projection queries and
864 recovered force calls, with the same maximum owner error. It verifies that
support outputs select the controller branch and feed later force clearing;
it does not establish original track selection or spawn/settling behavior.

## Connected load, environment and control producers

Three additional Python executors can wrap the remaining-child callback:

| Executor | Recovered stages | Explicit retained observations |
| --- | --- | --- |
| `DrivingLoads` | Initial normal loads, wheel projection, acceleration transfer, suspension correction, rolling resistance | Configuration, body angles, gear/torque inputs and resistance mode |
| `DrivingEnvironment` | Body resistance with density/weather/wind/drafting; axle vertical contributions | Track/weather/counter, body coefficients, distinct wind transform and ordered nearby cars |
| `DrivingControls` | Original input smoothing and output shaping | Raw input state, remote/gear services, service queries and publication of shared engine/brake fields |

Load routines use rear-record order `(0,1,3,2)`; tire/spin/controller forces use
consecutive order `(0,1,2,3)`. The adapters map results back explicitly.
Normal-load scaling shares the moment support-correction field. Transfer offsets
share the spin axle scales. Wheel projection reads current contact and spin,
and rolling resistance reads the same typed wheel class at original `+0xcc`.
Configuration mass remains separate from dynamic owner mass. The signed radius
fix is explained in [normal loads](calculations/normal-load.md).

Environment results update the controller force/moment accumulators and wheel
loads. Peer wake geometry survives into the next call. Control outputs update
raw tire steering, spin direction and service/other/parking controls before
force consumers run. Publication of engine flags and absent brake/engine fields
is mandatory. Preparation and other producers must synchronize context aliases:
for example, body pitch at `+0xbf4` is represented by both environment body pitch
and the load context's suspension-pitch observation. These records are not a
complete automatically initialized game state.

The [engine pipeline](calculations/engine-pipeline.md) connects its dispatcher,
torque and condition/thermal stages in Python and C++. The Python controller
also has the shared-state bridge described below. The [owner binding](calculations/owner-binding.md)
now produces inertia, mass and axle levers from explicit finalized configuration
and geometry; authentic assembly finalization remains required.

Run the larger comparison:

```powershell
python -m tools.driving_controls_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --actual-support
```

This passes 144 scenarios and 288 retained controller ticks: 192 supported and
96 low-support branches, 1,152 terrain queries and 864 tire-force calls. Actual
support transforms, input smoothing, all five load stages, body/environment,
tire-force stages and linear update execute inside the original controller.
Terrain projection, remaining preparation, gear services, engine, brakes,
mode queries and component delivery remain supplied. Without `--actual-support`,
the corpus retains its authored contact masks and checks 14 component-mutation
ticks and peer wake writes; all 288 ticks take the supported branch.

With actual support, maximum ordinary owner error is `0.00018310546875` and
maximum component argument error is `1.4551915228366852e-11`, under the same
recorded per-field tolerances. A near-zero yaw cancellation differs by two
float32 steps (`1.862645149230957e-9`); dividing forward velocity by that yaw
amplifies the next tick's turning-radius difference to `0.0013427734375`.
The oracle reports that derived difference separately and checks each radius
**exactly against its own preceding motion inputs**. Force and velocity
tolerances are unchanged. This records numerical conditioning rather than
claiming bit-identical multi-tick trajectories. Complete non-output bytes,
configuration bytes, ordered nested control calls and peer records are checked.

The shared comparison harness has extension hooks for subsystem initialization,
actual child selection, nested observations and extra output checks. This avoids
duplicating the complete controller emulator for every integration step; these
hooks are research tools and are not part of the stable mod API.

## Engine bound into the vehicle tick

`client/driving_engine.py` wraps the retained controls/load/environment executor.
It executes the recovered engine pipeline when the controller reaches its engine
call, then publishes outputs before brakes and tire forces run. This is Python
research integration; the complete connected controller is not yet a native
gameplay path.

| Shared original field | Producer/consumer handoff |
| --- | --- |
| `+0x474` | Controller vehicle flags and engine dispatcher |
| `+0xae4` | Smoothed control flags, engine activation/torque flags, then next tick's controls |
| `+0xa94`, `+0xa90` | Shaped throttle/service brake and engine inputs; callback writes return to force/control views |
| `+0xab4` | Engine RPM and later wheel-spin limit |
| `+0xa44`, `+0xa2c` | Controller local forward velocity/speed and engine cooling/effects |
| `+0xaa0` | Curve torque and the next suspension load correction; distinct from effective torque at `+0xaa4` |
| `+0xa69` | Selected gear byte, condition routine's mode and force direction; distinct from RPM helper gear index at `+0xb54` |
| `+0x34c` and weather/counter globals | Existing environment context and engine environment calculations |

Each explicit engine callback receives the current engine owner, controller and
force inputs. Shared aliases must be changed through the engine argument;
publication occurs before and after the callback and at pipeline completion.
Other controller/force fields remain available to the required wheel-drive
implementation. Configuration `+0x68c` aliases the existing assisted-gears and
third-system observations; inconsistent input views are rejected.

```powershell
python -m tools.driving_engine_pipeline_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --actual-support
```

The comparison passes 144 scenarios/288 retained ticks, with 192 engine calls
on supported ticks and 96 low-support ticks that correctly skip the engine.
It retains the 1,152 terrain queries and 864 tire-force calls. The corpus without
actual support executes 288 engine calls and 1,296 tire-force calls, including
14 component-mutation ticks. Supplied engine-setup/finalize mutations also check
throttle, flag and curve-torque publication across ticks. Nested engine call
order/arguments, control calls, configuration, complete owner and peer state are
compared. Maximum ordinary errors and the separately checked conditioned radius
are unchanged from the control/load/environment comparison above.

The original dispatcher, torque, RPM, curve, condition and thermal bodies run.
Engine setup/control, engagement/clutch, wheel-drive distribution, finalization,
brakes, terrain projection and remaining preparation are still supplied. These
results establish the connections, not a stock car's acceleration or handling.

## Brakes bound into the vehicle tick

`client/driving_brakes.py` executes the recovered brake/thermal routine in the
original engine → brakes → tires → correction → spin order. It retains
temperatures, countdowns, previous brake forces and parking ramp across ticks.
Shared inputs come from controls, engine flags, controller wheels, configuration
mass, pitch and environment. Wheel `+0xc` aliases spin slip ratio; `+0x94`
aliases its kinetic/inertia parameter. Brake quality (`+0xd10/+0xd14`) remains
distinct from spin quality (`+0xd18/+0xd1c`). The selected-gear inertia table
is required, as documented in [brake calculations](calculations/brake-forces.md#connection-to-the-vehicle-tick).

Brake longitudinal forces and spin adjustments reach subsequent force consumers.
The mandatory effect consumer receives wear/controller observations in original
interleaved order after the numeric stage. Mutation of later wheel observations
inside original component callbacks remains unverified. Authentic brake
configuration and inertia-table production remain required inputs.

```powershell
python -m tools.driving_brakes_pipeline_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --actual-support
```

With original support prediction this passes 144 scenarios/288 retained ticks:
192 supported engine/brake ticks, 96 low-support ticks, 1,152 terrain queries,
864 tire-force calls and 1,152 ordered brake observations. Original thermal,
fade, quality, weather-selector and brake bodies execute. Enabled and disabled
weather gates are exercised. Brake outputs are checked at the stage boundary
and final complete owner/configuration images. Maximum ordinary owner error is
`0.00048828125`; ordinary component argument and conditioned radius/component
errors are zero.

The authored-contact corpus completes 288 engine/brake ticks, 1,296 force calls,
24 component-mutation ticks and 1,728 brake observations. A derived secondary
wear observation differs by `2.9802322387695312e-8` on scenario 78's second tick.
Original spin is `10.56680679321289`, authored spin `10.566805839538574`
(one float32 step). Both projected speeds are `2.4678502082824707` and scale is
`0.2800000011920929`. Subtracting projected rotation from spin amplifies that
already checked input difference:

```text
observation = F32(min(F32(13.4109), abs(F32(spin - projected_speed/scale))) / 32)
original: 0.05478300154209137
authored: 0.05478297173976898
```

This exceeds the ordinary per-observation relative tolerance. The oracle reports
it separately as `maximum_conditioned_component_argument_error` and requires
each observation to match the formula exactly for its own source fields.
Other fields retain their existing tolerances. This does not prove bit-identical
trajectories or identical future wear accumulation. Maximum ordinary component
argument error is `5.4569682106375694e-12`.

These remain Python research connections. Stock-car initialization, remaining
preparation, terrain projection, gearbox services, engine setup/control,
engagement/clutch, wheel-drive distribution/finalization and component delivery
still block faithful driving. Native integration, original-client driving traces,
collision scenarios and live racing remain open.
