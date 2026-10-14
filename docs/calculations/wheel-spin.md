# Wheel-spin integration

The authored Python and C++ implementations recover the numeric state changes
of original `0x5400b0`. They operate on four wheel records, preserving original
float storage boundaries. This does not establish a complete drivetrain or the
frequency at which the caller runs.

## Inputs and update order

Each wheel supplies spin, spin adjustment, previous scale, projected speed,
normal load, kinetic parameter, ratio denominator, phase and contact flags.
Axle inputs supply base scale, compliance, secondary-angle parameter, quality
and lever length. Body inputs supply RPM, gear multiplier, yaw rate, lateral
velocity and a secondary-angle contribution. Their authentic component/input
producers remain required. Secondary-angle input units remain unresolved.

Here `f(x)` means storage as IEEE binary32, rather than rounding every arithmetic
operation. Wheel order is front pair, rear pair.

1. Store `spin = f(spin + adjustment / 32)`.
2. When correction is enabled, override is absent and direction mode is not 1,
   clamp spin to the positive/negative limit
   `f(max(abs(projected / old_scale), abs(f(RPM) * gear / old_scale)))`.
3. Store deformation as `f(load * f(0.001) * f(0.005))`, clamped to
   `[0, f(0.05)]`. Store squared spin separately, then kinetic value as
   `f(squared_spin * kinetic_parameter / 2)`.
4. Store `delta = f(deformation - squared_spin * base_scale *
   f(0.101936795) * compliance * f(0.001))`, clamp it to
   `[f(-0.01), compliance]`, then store `scale = f(base_scale - delta)`.
5. Store `phase = f(phase + spin * f(0.004973592))` and longitudinal
   local speed `f(scale * spin)`. Local vertical speed is zero; front lateral
   speed is `f(front_lever * yaw + lateral)` and rear lateral speed is
   `f(lateral - rear_lever * yaw)`.
6. Compute the event ratio as `f(scale * spin / denominator)`. A ratio above
   one produces an observed component call with amount
   `f(ratio * f(5.2083337e-6))`. Using the already stored longitudinal speed
   introduces an extra rounding step and changes this argument.
7. For nonzero projected speed, store slip ratio
   `f((scale * spin - projected) / projected)`, clamped to `[-1, 100000]`.
   Zero projected speed produces zero slip ratio.
8. Start secondary angle at `f(axle_parameter * f(0.0055555557))`.
   Contact adds the absolute body contribution scaled by 1.05 at the front
   or 1.02 at the rear. Quality above 0.75 adds
   `f((0.75 - quality) * f(0.07))`, with the recovered storage boundaries.
   Clamp the result to `±f(0.083333336)`.

For example, spin 10 with adjustment 32 first becomes 11. If correction is
disabled, that value enters the load-dependent scale calculation directly;
the prior scale is only used by the optional correction limit. Phase is carried
forward, not reconstructed from the current speed.

## Verification and boundaries

`python -m tools.wheel_spin_oracle <mcity.exe>` compares 2,592 bounded
original-function cases, checks all owner/configuration bytes and exact ordered
component-call arguments. Maximum numeric absolute error is
`1.52587890625e-5`, within `max(0.00025, abs(original) * 3e-7)`.
The native port matches the Python corpus exactly.

Only delivery through component method `0x591500` is supplied. Its receiver,
front/rear operation and five arguments are checked; actual wear/event effects
are not implemented by this comparison. The original caller, scheduler,
component producers and integrated car traces remain open.

Evidence: `ev_241c06acd8fe70639351e73ffaaef5d756e65fe3d62736fdb56fb4c9fd2cfe1f`.
Target SHA-256: `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Original bytes and decompiler records remain external/private.
