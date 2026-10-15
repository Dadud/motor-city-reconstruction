# Wheel speed projection

The original `0x53e030` calculates four longitudinal wheel-point observations.
It does not calculate tire force or a complete wheel-slip law. The reconstruction
in `client/wheel_speed.py` takes body motion, axle dimensions and four wheel
observations explicitly. No original table or asset data is included.

Source: x86 `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`;
retained REA evidence
`ev_08171ebc705221559a19a14811525b71efe23829d19f9c03f17676a9b0126876`.
This is static evidence supplemented by bounded original-function execution.

## Body motion at each wheel

The routine converts local yaw rate from turns per time unit using stored
`6.2831855`. It computes half-track yaw contributions for the front and rear.
Its consecutive wheel slots use these signs:

| Native slot | Lateral motion | Longitudinal motion |
| --- | --- | --- |
| 0 | body lateral + yaw radians × front offset | body longitudinal + yaw radians × front track / 2 |
| 1 | body lateral + yaw radians × front offset | body longitudinal − yaw radians × front track / 2 |
| 2 | body lateral − yaw radians × rear offset | body longitudinal − yaw radians × rear track / 2 |
| 3 | body lateral − yaw radians × rear offset | body longitudinal + yaw radians × rear track / 2 |

Keep consecutive slot order distinct from the explicit LF/RF/LR/RR processing
order used by the load-transfer module. The rear field order differs. Original
wheel identity/assembly mapping must establish the bridge before integration.

For a contacting wheel, the original halves its stored wheel angle and passes
that value to turn-based sine and cosine helpers:

```text
half_angle = stored_float32(wheel_angle / 2)
projected_speed = cos_turns(half_angle) × local_longitudinal
                  + stored_float32(sin_turns(half_angle) × local_lateral)
```

The final result is stored as float32. The API calls the input `angle` because
its upstream physical normalization is not yet established. Assigning it an
ordinary steering angle in radians would introduce an unsupported conversion.

For a wheel without contact, the result is simply the stored product of its
`spin_value` and `spin_scale`. Those inputs are named neutrally until their
upstream units are recovered. The airborne branch still writes a wheel result;
it does not preserve the earlier observation.

## Example and comparison

With zero yaw and zero wheel angles, all contacting wheels observe the body's
longitudinal velocity. At body velocity 20 and positive yaw, slots 0 and 3 receive
a greater longitudinal observation, while slots 1 and 2 receive a smaller one.
A non-contacting wheel with spin value −3.75 and scale 0.25 instead produces
−0.9375, independent of body translation.

Run the complete-function comparison with separately supplied original files:

```powershell
python -m tools.wheel_speed_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m unittest tests.test_wheel_speed -v
python -m tools.native_wheel_speed_compare build/native-check/mco_wheel_speed_compare.exe
```

The oracle executes the complete original routine and original sine/cosine
helpers with no substituted calls. All 1,296 scenarios pass, covering every
contact mask and positive, zero and negative body motion, yaw and wheel angle.
Maximum absolute error is `0` after correcting the intermediate store order:
the unrounded yaw conversion supplies separately stored half-yaw and axle-lever
products. This prevents carried wheel-spin drift in the
[connected drivetrain](drivetrain-stages.md). The recorded tolerance remains
`max(0.00025, abs(original) × 3e-7)`. Only four output fields may change; the full
owner image and configuration image are checked. Authored unit tests cover
slot signs, contact masks, angle projection, exact intermediate-store regression
and malformed input rejection.
The C++ port matches all 1,296 Python corpus cases exactly. Native tests and
comparison are included in Windows/Linux CI; local verification was on Windows.

Actual wheel angles, axle offsets and spin-state producers, integrated update
ordering, force consumers and real driving traces remain separate required work.
