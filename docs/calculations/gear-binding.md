# Gear-table initialization

`client/gear_binding.py` and `native/src/gear_binding.cpp` recover original helper
`0x539fe0` and enclosing numeric initialization through `0x53a5f6`. This supplies
previously synthetic arrays consumed by drivetrain, brakes and wheel spin. It
does not assemble a complete car or choose authentic stock ratios.

## Finalized inputs

| Configuration offset | Input |
| --- | --- |
| `0x70` | Signed maximum RPM |
| `0x228`, `0x22c`, `0x230` | Rear tire width in mm, aspect percent, rim inches |
| `0x32c` | Populated gear count, at most eight |
| `0x334`, `0x354` | Gear ratios and loss coefficients |
| `0x374` | Final-drive ratio |

`bind_finalized_gear_tables` reads those offsets from a complete `0x820`-byte
configuration. It requires an assembly-completion assertion, which records
caller responsibility but cannot certify arbitrary supplied data's provenance.

## Calculations

The original stores rear-tire circumference as:

`C = float32((2 * (width * float32(.001)) * (aspect * float32(.01))
              + rim * float32(.0254)) * float32(pi))`

It stores engine revolutions per second as `float32(maximum_rpm * float32(1/60))`.
For each populated gear, speed is that value divided by the unrounded product
`final_drive * ratio`, multiplied by circumference, then stored as float32.
A zero ratio/final-drive product instead produces zero speed. Maximum RPM
divided by the stored speed produces RPM-per-speed, or zero when speed is zero.
Slot 1 is explicitly overwritten with zero after the helper loop.

| Owner offset | Produced table or scalar |
| --- | --- |
| `0x1810` | RPM per vehicle speed, through the stored maximum-speed intermediate |
| `0x1830` | Reciprocal of the preceding table; float32 `.01` for populated zero entries |
| `0x1850` | Loss coefficient times final drive times gear ratio |
| `0x1870` | Gear ratio times float32 `.0014241834`; slot 1 overwritten with zero |
| `0x17f0` | Reciprocal of `(maximum_rpm - 250) * speed_per_rpm`, or zero when RPM-per-speed is zero |
| `0x18b0` | Final drive times float32 `.0154740065` |

The inertia-related constants retain their original values; their derivation and
complete physical units remain unresolved. Unused slots retain zeros. The API
preserves the neutral sentinel and signed RPM-subtraction wrap, and rejects a
zero near-limit divisor instead of emitting a nonfinite result.

For synthetic inputs 205/75 R15, final drive 3.5 and populated ratios
`(2.5, 0, 2.2, 1.7)`, active gears have distinct reciprocal speed factors.
Neutral has zero RPM-per-speed and inertia factor but speed-per-RPM sentinel
`.01`. Slots 4–7 remain zero. This example is not a particular stock car.

## Evidence and verification

Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Retained REA owner-initializer evidence:
`ev_28e6416fa219175f36704c6176745bd0ce2acf1e659f49956260fea80e9dd5f3`.
The helper and enclosing instructions were also inspected directly and executed
in the bounded CPU oracle; no new Ghidra session was needed.

```powershell
python -m tools.gear_binding_oracle '<original-install>/mcity.exe'
python -m tools.native_gear_binding_compare build/native-check/mco_gear_binding_compare.exe
python -m tools.driving_drivetrain_oracle '<original-install>/mcity.exe' --bound-gears
python -m tools.driving_drivetrain_oracle '<original-install>/mcity.exe' --bound-gears --actual-support
```

The original helper and enclosing loop match exactly in 225 cases, checking
all five eight-entry tables and the scalar, plus unchanged configuration bytes.
Coverage includes zero/positive/negative final drive, zero RPM, either side of
250, multiple tires including zero circumference, and 0/1/2/4/8 populated slots.
C++ matches Python exactly on the same cases. Local verification was Windows;
Linux CI is configured but not claimed as locally executed.

The producer-bound integrated runs each pass 144 scenarios / 288 repeated
controller ticks. Supplied contacts yield maximum owner error `.0001220703125`
and effect-argument error `1.8189894035458565e-12`. Recovered support yields maximum
owner error `.000244140625`, zero effect-argument error and 1,152 terrain queries.
Neither run requires conditioned comparison exceptions.

The connection exposed early rounding of the spin-adjustment denominator in
`0x548050` and two yaw contributions in `0x540710`. Python and C++ now preserve
their continuing x87 products. Comparison tolerances were unchanged.

Finalized component loading, authentic startup state, shift thresholds, terrain
projection, remaining preparation/services, component effects and collisions
remain required. These comparisons do not demonstrate a driven stock car or
a fan-server race.
