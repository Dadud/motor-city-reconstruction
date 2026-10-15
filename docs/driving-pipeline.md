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
