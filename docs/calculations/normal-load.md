# Support-mask initial wheel loads

The original helper `0x53d920` initializes the four wheel-force vectors before
later load corrections. `client/normal_load.py` reproduces all four 3D
force-vector writes from explicit support, attitude, component and motion
observations. `normal_load` exposes the four y-axis loads;
`normal_force_vectors` also returns the x/z zeros written by the original into
every vector.

Source `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Retained REA Evidence:
`ev_3ce59f9fae6e5945433fe36e417989cccb95f3593354d62e894b55e00e227174`.

## Support and redistribution

Inputs use LF/RF/LR/RR accumulator order. The original sums four support bytes.
The authored API accepts boolean observations, not arbitrary byte counts.
With fewer than two supporting wheels, or absolute pitch greater than 0.25,
the original clears all twelve force components and exits. At exactly 0.25
it remains active.

For supported configurations, it computes a front baseline from mass, wheelbase
and the rear lever; the rear baseline uses the front lever:

```text
factor = float32(mass × 0.5 / wheelbase)
front_baseline = float32(factor × rear_lever)
rear_baseline  = float32(factor × front_lever)
height = float32(height_parameter × float32(0.9090909))

c = float32(cos_turns(pitch))
s = sin_turns(pitch)
front_pitch = float32(((c - 1) × rear_lever - s × height) × factor)
rear_pitch  = float32(((c - 1) × front_lever + s × height) × factor)
bank_angle = float32(bank × float32(3.1415927))
front_bank = float32((front_baseline + front_baseline) × 0.5 ×
                     (height / front_track) × bank_angle)
rear_bank  = float32((rear_baseline + rear_baseline) × 0.5 ×
                     (height / rear_track) × bank_angle)
```

It applies turn-based sine/cosine pitch corrections and bank-dependent axle
terms. These are implemented with the original stored float32 boundaries rather
than an inferred suspension spring model. The `height_parameter` physical
interpretation remains incomplete.

- Four supports: both axles receive pitch correction and opposite half-bank terms.
- Three supports: the complete axle uses those terms; the single supporting wheel
  on the other axle receives both baseline loads plus twice that axle's pitch
  correction. Its unsupported partner is zeroed.
- Two supports on one axle: the two wheels receive the other axle's baselines
  plus opposite half-bank terms. The missing axle is zeroed. This branch does
  not add the ordinary pitch correction.
- Two supports across axles: each supporting wheel receives its axle's combined
  baselines plus twice its pitch correction. The other two are zeroed.

The source's branch-specific ordering is preserved, including rear accumulator
order. A generic equal split across the number of contacts would not match it.

## Final scale and clamp

After redistribution, the original computes:

```text
banking = clamp(abs(float32(sin_turns(bank) × speed² / curvature_scale)), 0, 6)
load_i = max(0, float32((wheel_scale_i - vertical_correction + banking) × load_i))
```

`wheel_scale_i`, `vertical_correction` and `curvature_scale` are explicit observed
inputs. The connected controller supplies its signed turning-radius field for
`curvature_scale`. Negative radii are valid: the original divides before taking
the absolute banking term. The API rejects zero to expose the unresolved singular
case instead of substituting a radius. Complete producers and units for the
other observations remain unresolved. The initial baseline
is not itself a final force in newtons. The implementation does not add gravity,
spring compression or a guessed damping law to these equations.

## Comparison and remaining work

```powershell
python -m tools.normal_load_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
python -m unittest tests.test_normal_load
python -m tools.native_normal_load_compare build/native-check/mco_normal_load_compare.exe
```

The Windows bounded run executes the entire original routine and its sine/cosine
helpers with no substituted calls. All 4,032 cases match the stored loads exactly.
It checks all four normal loads, the eight cleared force components and every
other owner/configuration byte. The decompiler's x87 return is not used as a
semantic output; the comparison excludes it. Cases cover every support mask,
both pitch signs and the exact attitude gate, both bank signs, banking saturation
and negative final-load clamping. The expanded corpus includes both radius signs.
Six unit tests cover masks, redistribution, gates and invalid observations.
The C++ port matches all 4,032 Python corpus
cases exactly, including all twelve vector components; its comparison is
included in Windows/Linux CI. The original comparison asserts the x/z clears
and unchanged remainder of the owner/configuration images against the translated
output rather than accepting the original's values for those components.

The authored API rejects malformed support masks, nonfinite values and invalid
mass/dimensions. These are API safeguards, not recovered original errors.
The [shared-state sequence comparison](../wheel-load-sequence.md) separately
checks handoff to the two later recovered load corrections.
Real support detection, motion/component input production and complete driving
integration remain required. See [load transfer](load-transfer.md),
[following suspension correction](suspension-load-correction.md) and the
[driving recovery map](../driving-recovery-map.md).
