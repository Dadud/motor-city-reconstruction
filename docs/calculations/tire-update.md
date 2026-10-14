# Combined steering and tire update

The authored Python and C++ `update_tires` functions reconstruct the complete
bounded behavior at `0x53ecf0`. They consume explicit wheel records, axle response
tables and four mode observations. They do not yet replace the playable
prototype's entire vehicle tick.

Source: x86 `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`;
REA evidence `ev_0379a76060060f4ff5eaa36c4c0fe3e98029ee951da14c7361a8d5d99e2651c6`.
Original files and decompiler output remain private research inputs.

## Inputs and ordering

Angles use turns. Trigonometric helpers multiply by stored float32 `2π`;
the inverse helper multiplies by `0.15915493667125702`. Scalar values are
normalized to float32 and original storage boundaries are retained.
Speed, acceleration, force and mass fields retain their observed names here;
their physical units and component producers require separate confirmation.
The numeric threshold `8.9406` alone does not establish speed units.

The four consecutive wheel records start at owner `+0x5fc`, stride `0x10c`.
Their last two slots must not be reordered to match another helper's load
accumulator order. This update reads projected wheel speed from each record;
the earlier `0x53e030` projection uses the preceding wheel angles. Moving that
projection after the new steering calculation would change the original
phase order.

| Wheel field | Record offset | Role |
| --- | --- | --- |
| Steering angle | `+0x00` | Replaced for all wheels |
| Slip angle | `+0x04` | Computed, optionally blended and clamped |
| Secondary angle | `+0x08` | Curve input, retained |
| Projected speed | `+0x10` | Selects slip sign, retained |
| Lateral force | `+0xd0` | Replaced |
| Normal load | `+0xd4` | Contact force input, retained |
| Longitudinal force | `+0xd8` | Retained for loaded contact; otherwise cleared |
| Secondary response | `+0xe0` | Replaced |
| Contact flag | `+0xec` | Gates both responses |
| Surface multiplier | `+0xf8` | Curve input, retained |

## Steering geometry

First multiply maximum steering by the recovered
[speed-dependent input response](steering-response.md). Below absolute steering
`0.001`, both front angles are equal. Otherwise the opposite wheel receives:

```text
paired = atan2(wheelbase, wheelbase / tan(abs(steering)) - front_track) / (2π)
```

The original tangent is the quotient of separately float32-stored sine and
cosine, rather than a direct tangent-library call. Negative steering assigns
the paired negative angle to slot 0; positive steering assigns it to slot 1.
The denominator is stored as float32 before the inverse helper.

Rear steering is zero unless enabled by the configuration. Through absolute
speed `8.9406`, both rear angles use `−0.2 × steering`, limited to
`±0.055555556`. Above that speed they use `0.5 × steering`, limited to
`±0.027777778`. All four final steering angles are limited to `[-1, 1]`.
For steering `0.08`, rear angles therefore change from approximately `−0.016`
at speed 8 to the high-speed limit `0.027777778` at speed 10.

## Slip and force sequence

At absolute speed **at most** `0.25`, yaw is multiplied by float32 `0.95`,
lateral acceleration becomes `−32 × previous_lateral_velocity`, and lateral
velocity becomes zero. These changes precede the per-wheel mode queries.

Each wheel separately queries the recovered [vehicle predicate](vehicle-gate.md).
When true, raw front slip is body slip plus the turn-valued angle of
`front_lever × yaw × 2π` against absolute longitudinal velocity. Rear slip
subtracts the corresponding rear-lever angle. When false, raw slip is zero.
Subtract steering for nonnegative projected wheel speed; add it for negative
projected wheel speed. Queries occur even for unloaded or unsupported wheels.

An unloaded or unsupported wheel clears lateral force, longitudinal force and
secondary response. For loaded contact at absolute speed **below** `0.25`,
secondary response is zero and lateral force becomes
`mass_parameter × 0.25 × lateral_acceleration`. For example, mass parameter
1300 and initial lateral velocity 0.2 produce acceleration approximately −6.4
and per-loaded-wheel lateral force approximately −2080. This calculation is
recorded without assigning unverified physical units.

At absolute speed `0.25` and above, the recovered axle
[response curves](tire-response-curves.md) supply both outputs. Below speed 6,
the slip passed to them is first replaced by:

```text
blend = (abs(speed) - 0.25) × float32(0.17391305)
slip = blend × slip + (1 - blend) × sin(slip × float32(2π)) × float32(0.008333334)
```

Store and clamp this slip to `[-1, 1]`. At exactly speed `0.25`, stabilization
has already run, but the curve branch runs rather than the stationary force
branch. At speed 6 the blend is skipped. After curve evaluation, absolute
lateral velocity below `0.25` subtracts
`lateral_velocity × float32(1.4) × sqrt(normal_load × 5700)` from lateral force.
Finally, absolute lateral force at most 10 is zeroed only above speed 6.

## Repeatable verification and limits

```powershell
python -m tools.tire_update_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m tools.native_tire_update_compare build/native-check/mco_tire_update_compare.exe
python -m unittest tests.test_tire_update tests.test_vehicle_gate
```

The comparison corpus covers speed boundaries and adjacent values, both control
signs, all 16 contact masks, zero/nonzero loads, front/rear curves, alternate
load mode, changing per-wheel predicate observations, reverse projected motion,
rear steering crossover, steering/slip clamps and force deadband cases.
Full owner and configuration images are checked for unexpected writes.
The original oracle executes actual steering, trigonometric, curve and predicate
helpers. Only the external interface's virtual operation 5 is supplied; its
receiver, operation number, owner argument and four calls are checked.

This remains a bounded calculation with synthetic tables and supplied state.
Actual curve construction, secondary-angle production, surface scaling,
predicate producer and counter scheduling, drivetrain/brake inputs, force
integration, collisions and repeated authentic driving traces remain required.
The comparison tolerance is `max(0.00025, abs(original) × 3e-7)`; observed errors
are recorded in the recovery ledger, rather than inferred from that tolerance.
