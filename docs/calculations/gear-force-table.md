# Original per-gear force table

`gear_force_table` translates the complete bounded producer at `0x53b260`
from executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
It calls the recovered torque interpolation at `0x548f00`; it does not substitute
a constant torque, sampled callback, or prototype engine model.

REA evidence: producer
`ev_376c42ddfd001a2652962d3b2361fb58e9798549b5d57fe5f079d41399888fe9`;
torque lookup
`ev_38e498015340681f1f22d7f40a90d90b9ad32d11cdb5642169b37851a9d4bf6e`.
The complete retained dossiers and binary instruction bytes remain private.

The inputs are the assembled 0x820-byte configuration, a caller-owned array of
eight RPM increments, and a selector from zero through seven. The result is
exactly 135 binary32 samples. The increment describes the table's independent
variable; it does not establish a simulation or network update rate.

## Fields and calculations

The configuration supplies signed idle and maximum RPM at `0x6c` and `0x70`,
26 torque knots beginning at `0x80`, rear tire width/aspect/rim at
`0x228/0x22c/0x230`, selector-specific gear factors at `0x334` and `0x354`,
and the final-drive factor at `0x374`. The first factor is a ratio; the second's
precise upstream meaning remains under recovery.

Let `S(x)` mean a binary32 store. Each decimal constant below represents its
stored binary32 value, promoted to binary64 for arithmetic. The original
startup x87 control word selects 53-bit arithmetic precision.

```
radius = S(((width * 0.001) * (aspect * 0.01) * 2 + rim * 0.0254) * 0.5)
multiplier = S(factor_354[gear] * ratio[gear] * final_drive)
r = ratio[gear] * final_drive                 # retained, not a float32 store
correction = clamp(S(r * 0.0025 * r + 1), 1, 1.5)

for i = 0 .. 134:
    rpm = clamp(S(i * rpm_increment[gear]), 0, 12000)
    if rpm < idle or rpm > maximum:
        output[i] = 0
    else:
        integer_rpm = nearest_even(rpm)
        torque = original_curve_interpolation(integer_rpm)
        force = S(torque * multiplier)
        output[i] = S(force / (correction * radius))
```

The output is a wheel-force table inferred from the torque/ratio/radius
relationship. This translation does not assert the downstream table's speed
units: its caller supplies the RPM increments. The correction is preserved
as observed arithmetic; no additional physical model is inserted.

For a zero RPM increment with idle RPM zero, all 135 entries are identical:
the zero-RPM torque knot is multiplied by the stored multiplier and divided by
the corrected radius. With positive idle RPM, those same samples are all zero.
Negative increments clamp to zero RPM; very large increments saturate at 12000.
Clamping happens before idle/maximum rejection, and RPM bounds are inclusive.

## Exactness and verification

The assembly is important here: the tire-width and aspect conversions are
retained intermediates until the radius store, the two ratio products have
different store boundaries, the torque product is stored before division,
and the denominator is not rounded to binary32 before division.

The supported authored interface requires a complete record, finite fields and
increments, selector 0–7, positive radius, and ordered RPM bounds within
0–12000. It rejects unsupported values rather than emulating original invalid
pointer access, nonfinite arithmetic, or x87 exceptions. Unused configuration
fields are not interpreted or normalized.

The original-executable oracle runs the complete producer and its real original
torque lookup and floor/conversion children. It launches no PE entry point and
implements no Windows imports. Its corpus covers all selectors, three ratio
regimes, varying tire geometry, inclusive/equal RPM bounds, negative/zero/large
increments, half-integer rounding, saturated RPM, and nonlinear torque knots.
It checks every output bit, surrounding sentinels, and unchanged input records.

Verification commands:

```
python -m tools.gear_force_table_oracle "<original-install>/mcity.exe"
python -m unittest tests.test_gear_force_table
python -m tools.native_gear_force_table_compare "<build>/mco_gear_force_table_compare.exe"
```

The corpus has 672 calls and 90,720 output samples. Native comparisons pass with
both MSVC and Zig/Clang using strict floating-point behavior. This demonstrates
the complete bounded function, not complete vehicle startup or driving.
