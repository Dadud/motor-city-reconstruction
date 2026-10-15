# Engine condition and thermal links

The engine dispatcher calls routines `0x546330` and `0x5464c0` under the working
names `gear_link` and `drivetrain_loads`. Their recovered bodies principally
update bounded gates, condition, three temperature-like fields and damage/effect
requests. They do not select gears or calculate wheel torque. The API retains
these dispatcher names for compatibility with the existing recovery map.

The temperature interpretation is inferred from the coupled heating/cooling
equations, ambient-like constant 20 and thresholds 90, 120, 130, 185 and 200.
The original units and component names have not been established. The stable mod
API must not expose these inferred names as verified physical units.

## Recovered inputs and storage

Every ordinary numeric state/configuration field is binary32. Integer catalogue
indices and RPM retain signed 32-bit representation. State is copied before an
update, and supplied child writes are rounded and checked before the next stage.

| State field | Original owner offset | Role established by the body |
|---|---|---|
| `gate_one`, `rate_one` | `0xce0`, `0xcf8` | Integrated/clamped gate |
| `gate_two`, `rate_two` | `0xce4`, `0xcf4` | Integrated/clamped cooling gate |
| `engagement` | `0xac8` | Coupling coefficient, clamped by the first routine |
| `auxiliary_temperature`, `auxiliary_capacity` | `0xacc`, `0xad0` | Second heat store and capacity |
| `main_temperature`, `loss` | `0xadc`, `0xae0` | Main heat store and associated loss output |
| `condition` | `0xad4` | Reference-scaled condition, upper bound 1 |
| `third_temperature` | `0xb58` | Optional third heat store, upper bound 185 |
| `shielding_one`, `shielding_two` | `0xd54`, `0xd58` | Subtracted from 1 in cooling terms |
| `drive_scale`, `primary_drive`, `alternate_drive` | `0xb00`, `0xb04`, `0xb08` | Heat-input factors |
| `request` | `0xcf0` | Conditional code-5 damage request |

Original flag bit `0x200` limits the cooling speed observation to 20; otherwise
the cooling speed is `max(abs(speed),1)`. The separate bypass observation
corresponds to global `0x9aaa64`; it sets main/auxiliary values to 100/125 and
caps condition at binary32 0.9, without invoking children.

## Gate and coupling calculation

Writing `F(x)` for a binary32 store and using binary32 constants:

```
gate_one = clamp(F(gate_one + 4.73175/(material_index+4)
                             * rate_one * 0.00013020834), 0, 1)
```

Disabled engines clear engagement. Enabled engines with `1-gate_one <= 0.2`
clear engagement and issue damage code 4 with value zero. Otherwise:

```
engagement = clamp(F(normalized_rpm*0.5
                     + auxiliary_temperature*0.0017142858 + 0.3), 0, 1)
```

For normalized RPM 0.4 and auxiliary value 125, engagement becomes approximately
0.7142857. With gate 0.8, engagement instead becomes zero and damage code 4 is
issued. The threshold compares the stored binary32 gate and constant, so values
adjacent to 0.8 are explicitly covered by comparison fixtures.

Auxiliary values above 200 issue effect-range code 23 with arguments
`F(0.0019999999/value), 0, 1, 0.25`. A request above 0.05 subsequently issues
damage code 5 with `F(request-0.1)`. Child mutations can change later decisions.

## Thermal integration

The second routine starts by integrating gate two with `F(rate_two*0.03125)`
within the full stored sum. Its reference-scaled condition is the initial
candidate for a cooling state. The primary or alternate heat coefficient is
selected using the original alternate-enabled byte and catalogue threshold,
then multiplied by integer RPM, drive scale and 0.03125.

When enabled by the catalogue, the third system uses:

```
capacity = 10.415999
cooling = F(cooling_speed*0.0001 + 0.002)
```

An enabled upgrade replaces capacity with
`F(upgrade_capacity*0.868 + 10.415999)` and adds its cooling coefficient. The
mode's catalogue coefficient multiplies the heat source by `1-mode_coefficient
+0.02`; mode 1 forces that heat source to zero. Cooling uses the first shielding
complement clamped to [0.2,1]. The resulting third value is limited to 185.
Above 130 it issues damage code 15 with `F(value*0.0076923077)`, followed by
effect code 24 with `F(current_value*0.00024038462)`. The latter rereads state
after the damage child: mutating 185 to 150 changes the following effect value.

Main cooling begins at 90, including equality. Its loss output is
`F((loss_index+1)*4*normalized_rpm)`. Transfer between the main and reference
stores includes catalogue transfer/capacity coefficients, speed-scaled cooling
above 90, and the first shielding complement. If the candidate exceeds its
reference, the routine clamps it and adjusts gate two using constant
0.000530504. A nonpositive cooling capacity bypasses this transfer.

Auxiliary coupling uses `F(material_index*0.0001+0.0005)` and engagement. Its
speed cooling begins strictly above 120, includes the second shielding
complement, and divides by `(1-gate_one)*auxiliary_capacity*1.92`. Zero
engagement sets the auxiliary value to 150 instead. The main store receives the
sum of auxiliary exchange, main/reference transfer, main cooling and drive
heating multiplied by its catalogue thermal gain.

The final condition is `min(F(candidate/reference),1)`; no lower clamp is
invented. Saturated condition or the earlier fully closed cooling gate emits
damage code 3, then effect codes 18 and 22. Main values above
`F(durability_index*10+250)` emit another code-3 request and effect code 18.
The implementation preserves the precise binary32 store boundaries and retained
intermediates; combining adjacent equations can change a boundary decision.

## Evidence and limits

Static REA evidence:

- `0x546330`: `ev_666ad5a328b851f0f2396a6ad75e7e1be3a9addcf69236ba4f3f29db0894d037`.
- `0x5464c0`: `ev_93f172b8530abd4d7631be96a4cd4d8c8d1f97bcfce2146070591d79fd4ce017`.
- Original executable SHA-256:
  `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

The bounded oracle executes both complete original bodies and checks owner
state, ordered child arguments and unchanged configuration. Damage routine
`0x5452c0` and effects `0x591180`/`0x591500` remain supplied boundaries. Fixtures
include deliberately mutated child state to verify subsequent rereads. These
checks do not establish the damage consumers, sound/effect presentation, full
vehicle integration or live race behavior. Incidental x87 return-stack values
are not a public result: the dispatcher does not consume them.

Singular denominators, absent mode coefficients and nonfinite inputs are rejected
by the authored interface; original invalid-input behavior is not reproduced.
This is a research API, separate from stable mod contracts. The original files
remain external inputs and are never modified by the comparison harness.
