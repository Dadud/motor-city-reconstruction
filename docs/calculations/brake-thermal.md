# Brake work, cooling and initialization

The authored `brake_thermal` Python/C++ module reconstructs the initialization
and thermal prefix of `0x538960`, stopping **before `0x538ca4`**. The rest of the
routine creates brake forces and applies wear and control branches; its
[complete numeric reconstruction](brake-forces.md) is now verified separately.
This prefix alone is not a complete braking model.

Target: x86 `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA evidence `ev_37d3f01d4022f494ae7b8ea87b92ac5236f20843089b5167f101248bb4487b92`.
Original files and pseudocode remain private inputs.

## Observed calculation

The two axle records supply temperature, diameter, cooling coefficient, heat
capacity factor, thermal mass, temperature limit, material/construction codes
and an integer countdown. Four prior brake forces, wheel-spin values and scale
factors supply work. Service and parking controls are explicit observations;
their input/controller mapping has not been recovered.

Ambient observation is 5 when the environment flag is set, otherwise 15; world
query codes 1 and 2 subtract 10 and 20 respectively. These are observed numeric
temperature values. The current verification supplies this external world query
result rather than claiming its original environment producer is implemented.

At absolute speed greater than 1, nonzero service control enables front work.
Rear work runs for parking control, or for service control with a rear scaled
spin magnitude greater than 1. Axle work sums absolute brake-force/spin products
and multiplies by `1/32`, retaining the original intermediate float32 stores.
This factor alone does not establish the scheduler rate.

For each axle, the thermal update consumes:

```text
cooling_work = (temperature - ambient) × diameter² × 0.25 × float32(π)
               × cooling_coefficient × float32(abs(speed) + 5)
new_temperature = temperature + (brake_work - cooling_work) × float32(0.001)
                              / ((thermal_mass + thermal_mass) × heat_capacity_factor)
```

Store the result float32 and cap it at twice the supplied temperature limit.
With service control zero, reset the countdown to a recovered material-based
diameter calculation plus 64; otherwise decrement it with a floor of zero.
The diameter calculation stores `diameter × float32(39.370098)`, rounds to the
nearest even integer, adds material offsets `1→16,2→8,3→32`, and adds 8 for
construction code 1. For diameter 0.25, material 2 and construction 1, the
countdown reset is `10 + 8 + 8 + 64 = 90`.

The stage also stores speed-squared times mass times 0.5 and mass times the
supplied elevation parameter times float32 9.81, then clears all four previous
brake-force outputs. Their later replacement is outside the verified prefix.
The module includes the statically recovered fade helper: full response below
the limit, a linear decline through the next 50 units, and a floor of 0.5.
The prefix oracle does not execute that later fade call.

## Verification and exclusions

```powershell
python -m tools.brake_thermal_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m tools.native_brake_thermal_compare build/native-check/mco_brake_thermal_compare.exe
```

All 432 prefix cases match exactly, with actual original countdown and ambient
helpers; only the ambient world-query result is supplied. The full owner and
configuration images are checked for unexpected writes and query count. The
native port matches the same Python corpus exactly. Cases include service and
parking combinations, reverse and adjacent speed gates, high-temperature caps
and all represented environment modes.

Thermal units, authentic component coefficients and environmental producers,
component degradation/event delivery and input control mapping remain required
before claiming original braking. Invalid thermal denominators
are rejected by the authored API; that policy is not original error handling.
