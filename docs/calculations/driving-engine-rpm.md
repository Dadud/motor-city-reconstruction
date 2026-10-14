# Driving engine RPM and torque coupling

The reconstructed driving RPM helper is the complete original `0x546e70`.
The torque coupling preceding it is the bounded original interval
`0x547932`–`0x5479fe` within `0x547120`; earlier torque, boost, damage and
temperature producers are outside this interval. These routines are not yet
a complete engine, transmission or vehicle update.

## RPM update

Let `n0` and `n1` be configuration idle and maximum RPM; `t` is the throttle
field, `r` the previously normalized RPM field, `q` the carried target RPM.
The original first computes:

```
requested = clamp(n0 + nearest_even(float32(t × float32(1.1) × (n1 − n0))), n0, n1)
q_next = q + nearest_even(float32((requested − q) × exp(−r) / 16))
```

The exponential is executed by original x87 instructions, not replaced with
an oracle stub. The authored implementations use the host exponential under
the recorded comparison range. Integer conversion follows a float32 store;
rounding ties go to even. No engine scheduler frequency follows from `/16`.

When the engine-enable bit is clear, its raw acceleration contribution is zero.
Otherwise it is the stored product of owner fields `+0xb28` and `+0xaa8`.
The output at `+0xab8` multiplies that product by `1 − r`.

For negative raw acceleration, the output is bounded below by `r × −200`.
The angular-speed increment is the smaller of that output divided by 32 and
the target-speed correction multiplied by owner `+0xb28` and divided by 32.
Both candidates are stored floats before their minimum is taken.

For nonnegative raw acceleration below target RPM, the original advances
angular speed, converts it to integer RPM and prevents it exceeding the
target. Otherwise, gear slot 1 skips road-speed coupling. Every other slot
raises the target to at least the absolute rounded product of that slot's
owner `+0x1810 + 4 × gear` value and longitudinal speed `+0xa44`.

Final enabled RPM is clamped first to owner `+0xac0`, then to the minimum
provided by the caller. Disabled engines finish with zero RPM and angular
speed, but still update their target. RPM-to-angular-speed uses original
float constant `0.10471976`; the inverse uses `9.549296`.

For example, idle 600, configured maximum 7000, throttle 0.5, previous target
2400 and normalized RPM 0.5 produce requested RPM 4120 and a smoothed target
2465. The final RPM also depends on previous angular speed, acceleration,
enable state and road-speed coupling.

## Torque coupling before the RPM call

The earlier part of `0x547120` supplies curve torque `C` at `+0xaa0` and
effective torque `T` at `+0xaa4`. This tail computes:

```
power = max(float32(RPM × C × float32(0.00010471976)), 0)
drag = float32(owner[0xb24] × owner[0xb6c])
corrected = environmental_correction × T − drag
```

The complete environmental helper `0x535e20`, including its `0x594030`
selector helper, executes in the original comparison. Its owner input is
`+0x34c`; its external inputs are three global mode/selector values.
Their game-level producers and the owner's physical interpretation remain
unresolved. The correction is a stored float clamped between the original
float constants 0.95 and 1.05. It combines that owner field plus 500, a
mode-dependent base of 288.15 or 278.15, and selector-dependent subtraction
of 10 or 20. Names in the public API deliberately retain these uncertainties.

With engagement `e = owner[0xb2c]` and resistance `R = owner[0xb3c]`, the
next acceleration input at `+0xaa8` is:

| Observed branch | Acceleration input |
| --- | --- |
| Gear slot 1, or `e = 0` | `corrected` |
| Other gear and `e ≥ 1` | `−R + min(corrected, 0)` |
| Other gear and nonzero `e < 1` | `(1 − e²) × corrected − R` |

The original retains its unstored intermediate corrected torque through these
branches. The final branch results and corrected torque are stored float32.
An engagement of 0.5, corrected torque 100 and resistance 12 produces
acceleration input 63. Full engagement with the same positive torque produces
−12. These observations do not establish how clutch input becomes engagement.

## Evidence and verification

Complete RPM evidence:
`ev_3c8099ab7007ea9a2eb5f2aaa8d0f9810ddcb1d07efdde478a912e3a8402e7d7`.
Engine dispatcher evidence:
`ev_f4138fe586f7a644826c3fed0bf4ac2ff952ab9063efe9cdcc51b1623111253b`.
Torque-update evidence:
`ev_287a64b85764bf6ac1fd3474ee9c2a7a25b31ff198369aedd2755021570487c8`.
Environmental-helper evidence:
`ev_7e06c39a5c9c60ba3519265f02d1dc9458de0d0b7f1c34fe0cff9e4d30783f5b`.
Original instructions were executed from the locally supplied executable with
SHA-256 `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
No executable bytes are distributed.

The original RPM comparison covers 2,592 combinations of enable state,
normalized RPM, throttle, acceleration sign, prior RPM, gear slot and signed
road speed. All four output fields match exactly. The original torque tail
comparison covers 868 combinations including engagement boundaries,
negative torque, reverse drag and environmental clamp extremes. Its four
written output fields match exactly. Neither comparison substitutes calls;
both reject unmodelled writes anywhere in the owner image.

The Python and C++ counterparts have matching differential corpora. Their
validation boundaries reject nonfinite inputs and unsupported integer/range
values rather than claim original malformed-input semantics.

## Remaining work

Recover actual gear ratios, gear selection and engagement producers before
connecting these routines to a car. Complete `0x547120` includes torque lookup,
damage-dependent modulation, auxiliary losses, boost, durability events and
additional callers; its retained pseudocode loses x87 stack arguments in two
power calls, so instruction-level recovery is required. `0x546330` and
`0x5464c0` update component health and temperature-related state and dispatch
events; their addresses alone do not prove differential or clutch behavior.
The dispatcher `0x545af0` selects several driving modes and remains unported.
