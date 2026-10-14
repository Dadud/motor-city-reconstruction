# Combined-slip force limiting

The Python and C++ implementations reproduce numeric force limiting in original
`0x53fb30`, including its slip curve `0x53f990`, loss observer `0x53fe40`
and square-root helper `0x6f13a0`. Component effect delivery remains external.
This is a recovered consumer of supplied force/contact state, not a complete
tire model or differential.

## Rear transfer and slip curve

Without parking control, a rear wheel whose positive longitudinal force exceeds
`f(normal_load * primary_coefficient)` transfers the smaller of its excess and
the other rear wheel's spare capacity. This precedes per-wheel limiting.
The transfer conserves the pair's force; subsequent limiting need not.

The following factor applies only when **signed vehicle speed is greater than
one**. Reverse motion and speed exactly one use factor one. Here `s` is the
binary32 slip ratio; constants and intermediate stores follow the implementation.

| Slip interval | Factor |
| --- | --- |
| `s <= -1` | `max(0.125, abs(f(0.5 / s)))` |
| `-1 < s < -0.2` | `f(f(0.875) - abs(f(s * f(0.375))))` |
| `-0.2 <= s < -0.05` | `f(s * f(-4.375))` |
| `-0.05 <= s <= 0.15` | `1` |
| `0.15 < s < 1` | `f((1 - s) * f(0.4117647) + f(0.65))` |
| `1 <= s <= 8` | `f(f(0.7071) - s * f(0.0571))` |
| `s > 8` | `max(0.0625, f(2 / s))` |

The negative boundary at -0.05 is discontinuous: exactly the float boundary
uses one, while a value immediately below it produces approximately 0.219.
This recovered behavior is retained rather than smoothed. For example, slip
ratio 2 produces approximately 0.5929 when vehicle speed exceeds one.

## Force limiting and effects

First observe loss `f(1 - factor)` and scale longitudinal force by the factor.
Slip below `f(-0.05)` also multiplies it by `1 - axle_quality / 2`.
Store magnitude `f(sqrt(lateral² + longitudinal²))`, primary capacity
`f(primary_coefficient * load)` and secondary capacity
`f(secondary_coefficient * load)`. Alternate mode scales both capacities by
the slip factor.

If magnitude exceeds primary capacity, scale lateral and longitudinal forces by
`f(sqrt(f((secondary_capacity / magnitude) * f(0.99))))`; observe the associated
loss. Scale secondary response separately by `secondary_capacity / magnitude`.
The reduction is not clamped to one. These equations must not be replaced with
an inferred friction-circle normalization.

Loss observation skips zero loss/load/coefficient and absent contact. Depending
on component code, vehicle code and wear mode it first emits a constant component
update amount `f(5.2083333e-6)` with parameters `(0, 1, 0.25)`.
Positive clamped `f(loss * primary_coefficient)`, positive slip and positive
vehicle speed produce a further update with parameters
`(f(0.15), f(0.000052083335), 0.25)`, followed by a secondary observation
`f(min(f(13.4109), abs(f(spin - projected / scale))) / 32)`.
Operation order and front/rear receiver arguments are preserved.

## Verification and boundaries

`python -m tools.combined_slip_oracle <mcity.exe>` executes 1,296 complete
original numeric paths. Maximum absolute error is `0.00048828125`, within
`max(0.0005, abs(original) * 3e-7)`. It checks complete owner bytes and exact
ordered effect arguments. The native port matches the Python corpus exactly.
Original curve, loss observer and square-root code execute; only component
delivery methods `0x591500` and `0x591180` are supplied.

Authentic forces, coefficients, contact production, actual component effects,
caller branches and repeated integrated car behavior remain required.
Evidence IDs:
`ev_e457365c7453a1dde83238fe470de5d5e52c4b2134c940474ad54a0ffc2eaef1`,
`ev_d200a9558cc633edb5c56c722b5977b40cd5d8bf9e9d1ffab10ee9d1bc4cdb82`,
`ev_c238084a158e765465c70f122be215ed03b4440cca0bf3c6b995ec60dec0b0a9`,
`ev_d55dd756c53dcb9106fa1d12eafe3cb6bbc9e99ee878cb7467c83c035b6e6c64`.
Target SHA-256: `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
