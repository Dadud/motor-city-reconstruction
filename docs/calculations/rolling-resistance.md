# Original wheel resistance contribution

`0x53e3d0` adds a direction-dependent resistance contribution to the four wheel
longitudinal-force accumulators. The authored implementation is
`client/rolling_resistance.py`. This is one contribution in the active force
path, not complete braking, traction or drivetrain behavior.

## Gates and inputs

The helper does nothing when absolute longitudinal body speed is below 2,
owner flags contain `0x200`, or predicate `0x55fc30` returns nonzero. The speed
and flag tests short-circuit before querying that predicate. Its gameplay meaning
and producer remain unresolved and are explicit observations in the authored API.

For each wheel, the original reads slip state, a surface identifier, normal load,
rolling speed, a speed scale, a contact byte and accumulated longitudinal force.
Front and rear component coefficients and adjustments are distinct inputs. Their
complete catalogue meanings and units remain to be established.

The decompiler displays surface identifiers as tiny floating-point values, but
the instruction comparisons use their stored 32-bit patterns. Identifiers 2,
3 and 5 therefore select branches as integer IDs, rather than mysterious
floating-point tuning values.

## Equations and ordering

For absolute body speed `v`, the surface coefficient is:

| Surface ID | Coefficient |
| --- | --- |
| 2 | `float32(v × float32(0.000096) + float32(0.012))` |
| 3 or 5 | `float32(v × float32(0.000072) + float32(0.013))` |
| Other | `float32(v × float32(0.000048) + float32(0.01))` |

The applicable axle factor is `(adjustment + 1) × component_coefficient`, stored
as float32. The original cosine helper `0x6f13c0` computes cosine after multiplying
its input by the executable's float32 `6.2831855`, so the body-angle input uses
turns. This does not establish the normalization of wheel slip state.

The normal branch projects resistance with `cos(abs(body_angle) × 6.2831855)`.
The alternate global branch additionally multiplies by a slip amplification:

```text
d = float32(abs(wheel_slip × 180))
amplification = clamp(float32((d×0.0831 + d²×0.0988)×0.5 + 1), 1, 8)
contribution = float32(-projection × normal_load ×
                       float32(axle_factor × surface_coefficient × 0.5))
```

Decimal coefficients in the implementation use the original float32 values.
Negative wheel rolling speed reverses the contribution's sign. The helper adds
it only if the contact byte is nonzero, load is nonzero and
`1 / speed_scale < abs(rolling_speed)`. The speed test is strict: equality does
not add a force. The original computes a contribution even when this application
gate fails.

The return value is the **last wheel's computed contribution**, not the sum of
four contributions and not necessarily an applied force. Early gates return zero.
The authored API rejects nonfinite observations, negative loads, nonpositive
speed scales and invalid surface IDs; those are interface safeguards.

## Evidence and comparison

The source SHA-256 is
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA Evidence:

- Complete resistance helper: `ev_d17d86e72fb79295ebda254d80c690e40ec146b8c1bf0682877187063889f507`.
- Original turn-based cosine: `ev_34944e67a3db31f2e7ead85698993f307bf645dce3dfc7aed21bdfac6ea340cf`.

```powershell
python -m tools.rolling_resistance_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
python -m unittest tests.test_rolling_resistance
python -m tools.native_rolling_resistance_compare build/native-check/mco_rolling_resistance_compare.exe
```

The Windows oracle executes the complete original helper and original cosine
with isolated synthetic owner/component state. Only the mode predicate is
substituted. All 1,344 cases pass, with maximum stored-force error
`0`, under tolerance `max(0.00025, abs(original)×3e-7)`, after correcting the
intermediate store order: axle and coefficient remain unrounded until their
combined product is stored. This also removes upstream drift in the
[connected drivetrain](drivetrain-stages.md).
It compares each force accumulator, checks every other owner byte unchanged,
checks the return value and verifies the predicate call gate. Cases include both
speed signs and the exact speed-2 gate, all surface branches, zero load, three
contact masks, threshold equality and either side, both mode gates, body-angle
projection and alternate amplification. Execution is bounded and no sockets or
host callbacks run.
The C++20 port matches the same 1,344 Python scenarios exactly, including full
wheel observations and the final contribution. Its native unit check and
comparison are included in Windows/Linux CI; this local run was on Windows.

Upstream component values, surface lookup, contact state and integration with
other longitudinal-force contributions remain required. See the
[driving recovery map](../driving-recovery-map.md) for the enclosing call order.
