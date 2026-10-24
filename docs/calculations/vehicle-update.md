# Original vehicle update controller

`client/vehicle_update.py` and `native/src/vehicle_update.cpp` reconstruct the
controller-owned arithmetic and dispatch in original `0x53c140`. The stage
executor is mandatory: child stages can change typed vehicle state, and queries
return explicit observations. State writes round to binary32 before the caller
consumes them, including branch thresholds; query returns remain separate.
This boundary permits recovered stages to be
connected without silently substituting guessed behavior for missing stages.
It is not yet the complete playable force solver.

## Branches and stage ownership

The controller observes global mode before testing whether the vehicle is active.
An inactive vehicle receives no further child calls. An active alternate-mode
vehicle takes a separate path: it projects velocity, predicts support, prepares
the vehicle, updates control smoothing and steering/wheel projections, sets supported wheel loads
from `mass * float32(2.4525)`, updates wheel spin/phase and calls the engine.
It does not run the normal tire sequence or the usual post-update tail.

The normal path prepares the vehicle first. It computes turning radii from
world longitudinal speed divided by each selected angular component times
`float32(2π)`; zero angular speed uses the original 4,000,000 sentinel.
It stores horizontal local speed as the magnitude of lateral/longitudinal
velocity, negating it for reverse longitudinal motion. Its secondary angle is
`atan2(local_lateral, abs(local_longitudinal)) * 0.15915493667125702`.
Support prediction and bookkeeping then precede these choices:

| Path | Condition after child stages | Controller behavior |
| --- | --- | --- |
| Tilted | Explicit tilt flag or attitude below `float32(0.85)` | Clear unsupported/zero-load wheel forces; call tilted motion and refresh; reproject velocity |
| Flagged | Either flag bit `0x2` or `0x200` | Call the flagged-motion child and return immediately |
| Low support | Fewer than two contacting wheels | Clear all wheel forces, apply body gravity, call linear update and body moment inputs; select airborne angular behavior |
| Supported | At least two contacting wheels | Prepare loads and surface coefficients, dispatch the recovered force stages, accumulate/integrate motion |

The supported path projects prior acceleration and extra acceleration into local
coordinates before normal-load processing. Surface selection uses the supplied
record's low five bits, or the explicit fallback class. Grip uses environment,
signed speed magnitude, wheel type, quality, axle observations and an external
32-entry surface coefficient table. This table must come from authentic loading
before game acceptance; comparison fixtures use authored coefficients.

Two successive vehicle-gate observations are independent. The first can clear
local state; the second controls wheel-spin integration and combined-slip
limiting. A false first query therefore does not imply the second is false.
The supported child sequence is:

```text
wheel projection → control smoothing → moment inputs → body forces
load transfer → suspension loads → resistance → engine → brakes
tires → wheel correction → [wheel spin → combined slip]
[force orientation] → body moments → linear update
```

Before load transfer the controller clears local vertical acceleration. Before
force orientation/body moments, each wheel whose threshold is strictly below
the negative reference has all three forces cleared. Orientation has its own
global gate. Surface, input, engine and other child producers remain required.

## Motion arithmetic and inactive linear behavior

Controller matrices use row vectors. Each output stores to binary32 after the
ordered sum `(x * m0 + y * m1) + z * m2`. Angular velocity receives its recovered
`acceleration / 32` increment after local-to-world transformation. Supported
wheel forces accumulate in slot order `2, 3, 1, 0`. Positive total vertical force
selects the force-sum path; otherwise the lateral contribution is copied directly.
Very small local lateral acceleration is zeroed. At more than two supports and
speed magnitude below 6, a small local angular middle component is also zeroed.
The threshold comparisons are strict, with original float constants preserved.

Inputs retain original numeric conventions: linear velocity uses metres per
second, while native body angular velocity uses turns per second. The secondary
angle above is in turns, not radians. This differs from the earlier portable
pose helper's radian API; an adapter must convert explicitly rather than mixing
the conventions. Authentic component-to-controller input assembly remains open.

`apply_linear_update` reproduces complete numeric behavior of `0x540c30` after
its supplied vehicle-gate query. Enabled mode adds world acceleration divided
by 32 to world linear velocity. Disabled mode projects both velocities, retains
only the middle local linear component and the first/third local angular
components, transforms them back, and clears world linear/angular acceleration.
With identity matrices, velocity `(1,2,3)` becomes `(0,2,0)` and angular velocity
`(4,5,6)` becomes `(4,0,6)` in disabled mode.

The tilted and low-support branches also call `0x548260`, now recovered and
named `engine_system_update`; the exact recovered body is documented in
[vehicle-path engine controller](engine-system-update.md). It was previously
mislabelled `refresh_motion` based on call position alone.

Normal tilted/low-support/supported paths run post-update work, followed by a
short-circuited optional follow-up. Inactive, flagged and alternate paths bypass
that tail. The [scheduler](../scheduler.md) separately establishes list ordering
and alternating force/pose dispatch; the arithmetic constants do not establish
an independently verified wall-clock rate.

## Verification and outstanding integration

`python -m tools.vehicle_update_oracle <mcity.exe>` executes all original
controller instructions in a bounded emulator. Its 2,607 cases cover all six
paths, reverse/zero/low/high speed, contact masks, independent gates, surfaces,
orientation, short-circuiting and child mutations. Twenty focused cases change
attitude, support, forces or motion during a supplied child call, including
values that round onto opposite sides of the attitude boundary. Another 1,452
cases execute the actual original `0x540c30` inside the controller, covering both
linear-gate results. Ordered controller calls and all owner bytes are checked.
All compared numeric outputs match exactly in this corpus, under comparison
tolerance `max(0.0005, abs(original) * 4e-7)`; the native port also matches Python
exactly. This is not a proof of equivalence for every possible floating-point input.

The native `make_driving_load_executor` connects normal-load initialization,
acceleration transfer and suspension-load correction to the controller using
explicit configuration observations. It delegates the other child bodies and
gate observations. The actual original angle helper executes. Comparison
coverage does not prove those missing child producers, authentic assembled-car
inputs, collision/contact creation, component effects or end-to-end driving.
The native controller is available in the core; the playable prototype is not
switched to an incomplete executor.

Evidence: controller `ev_6691a574a2c8313463ca5c8b1ffb2fa16c4305a4463d43be27ab00b2f64f2e84`;
linear update `ev_07e93f4c881dfdfb041e72a77c4da190278fe07871d1fbb763170843858794c2`.
Target SHA-256: `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Original bytes and decompiler records remain private/external inputs.
