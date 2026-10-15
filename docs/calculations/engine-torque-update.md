# Driving torque update

The complete body at `0x547120` calculates driving torque, applies engine
condition effects, drives the recovered coupling/RPM update, and submits
damage/effect requests. It operates separately from the dyno cylinder solver.
The first complete implementation is `client/engine_torque_update.py`, with
the equivalent native calculation in `native/src/engine_torque_update.cpp`.

## Inputs and update order

RPM, idle/maximum/limiter RPM and catalogue indices are signed integers.
Ordinary numeric owner fields, torque knots and catalogue coefficients are
binary32. The implementation preserves stores and intermediates independently
of the host's floating-point evaluation mode.

The routine first stores `normalized_rpm = F(incoming_rpm/limiter_rpm)`, before
checking the enabled bit. A disabled engine clears RPM, angular speed, effective
torque and engagement. An enabled engine below idle sets RPM to idle, obtains
effective torque from the idle curve and halves engagement. Both paths leave
the earlier curve-torque field intact and still enter the coupling/RPM tail.
Recomputing that field or normalized RPM at this point changes original behavior.

At or above idle, the same adjacent 500-RPM interpolation recovered for the
engine dispatcher stores curve torque. The throttle observed on entry remains
the input for later gain decisions, while several following operations reread
mutable owner fields after child calls.

With zero or negative throttle, effective torque is the negative absolute value
of the unstored interpolated torque times normalized RPM and binary32 0.35
(or 0.18 with the catalogue's third-system flag). Query `0x55cfc0` determines
whether to multiply this by `1-brake_control`; only its low byte is tested.
Flag bit 8 is cleared.

Positive throttle takes the following stages in order:

1. Advance/clamp the condition accumulator and select a damage pulse.
2. Multiply curve torque by the pulse factor.
3. Deduct loss, auxiliary-temperature and upgrade terms.
4. Clamp effective torque below at zero and apply the nonlinear throttle curve.
5. Update flag bit 8 and apply the catalogue gain mode.
6. Run eligible boost, or exhaust-tag effects and damage.
7. Calculate power, environment correction, drag, coupling and RPM.
8. Submit overspeed/overload damage and associated effects.

## Condition pulses and torque deductions

Unless bypass is active, a condition gate below 0.25 clears the accumulator.
Otherwise, `normalized_rpm*throttle` selects a binary32 increment: +0.005 above
0.6, +0.002 above 0.35, or -0.001. The stored result is clamped to [0,1].

The accumulator and five damage observations select a call to `0x4b7170` in a
strict priority order. Its time input is `F(counter*0.015625)`; the other
arguments are `(0.5,0.02,0.25)`, `(2,0.02,0.9)`, `(1,0.02,0.5)` or
`(0.33,0.02,1)`, with the first branch complementing the returned value.
The result is stored and clamped to [0.2,1]. The pulse producer remains an
explicit supplied boundary, rather than an invented waveform. Bypass uses 1.

Loss torque is:

```
F(loss * 60000 / (rpm * F(6.2831855)))
```

It is clamped between zero and `F((loss_index+1)*10)` before subtraction.
Auxiliary values strictly above 120 introduce another deduction proportional to
`(material_index+1)*normalized_rpm*1.5`. Enabled catalogue upgrades add a term
proportional to `2*(upgrade_index+1)*normalized_rpm`. Both are converted using
the same `60000/(rpm*F(6.2831855))` scale. Units and the physical identity of
these inferred temperature/loss fields remain unconfirmed; no new model is
substituted for their original equations.

## Nonlinear throttle response

The original uses two complete CRT power calls, not an unspecified multiplier.
Their constants were read from the verified executable:

```
reduction = clamp(F((1-throttle)^6.294926643371582
                     * F(2.1532740592956543)
                     * normalized_rpm^0.5177839994430542), 0, F(0.98))
effective_torque = F(effective_torque - reduction*effective_torque)
```

For throttle 1, reduction is zero. For throttle 0.7 and normalized RPM 0.5,
reduction is approximately 0.000769: the calculation preserves nearly all of
the torque available after deductions. The earlier coasting branch handles
throttle zero, so the power formula does not determine its engine braking.

Entry throttle above binary32 0.3 enables catalogue gain modes 2–5, using 1.03.
Modes 3 and 4 use 1.0609 above binary32 0.8. Both effective torque and stored
curve torque receive this gain. The original clamping range is [1,1.1].

## Boost, output and damage

Boost is eligible when the alternate-enabled byte is set, the observation is
below its threshold, the exhaust tag is zero, catalogue availability is
positive and RPM is strictly below configured maximum minus 500. The original
`0x549580` produces an x87 torque result and a binary32 increment through a
pointer. The authored callback returns both values explicitly. The increment
is added to the observation, and the torque is added independently to effective
and curve torque. The routine also sets owner flag `0x11c0` to 1.

A nonzero exhaust tag follows a separate ordered effect path based on absolute
motion and compression. Sound/effect consumers remain supplied operations;
these requests do not establish their visual or audible presentation.

The output tail executes the recovered environment helper `0x535e20`, calculates
drag, applies the original neutral/partial/full engagement rules and runs the
complete RPM helper `0x546e70`. Power is calculated before the RPM update,
using curve torque; this routine does not recalculate it afterwards. Details of
the tail are also recorded in the existing drivetrain coupling writeup.

After RPM changes, damage requests follow the original order:

| Code | Trigger/input |
|---|---|
| 7 | RPM above `(durability_index+1)*500+5500`; squared excess times 8e-8 |
| 9 | RPM above supplied `0x54d250` limit; excess times 8e-8 |
| 14 | RPM above `overspeed_base+250+overspeed_extra`; squared excess times 8e-8 |
| 8 | Curve torque above a catalogue product; squared scaled excess, bypass-sensitive |
| 12 | Curve torque/capacity above 1; ratio capped at 5, doubled squared ratio |

Children may mutate state, and following triggers reread it. For example,
mutation of RPM by the supplied limit producer can alter later overspeed
requests. Original damage code 7 also submits five effects in order: 17, 18,
23, 19 and 20. The code-12 path subsequently submits effect 24.

## Verification and limits

REA evidence for the complete routine:
`ev_287a64b85764bf6ac1fd3474ee9c2a7a25b31ff198369aedd2755021570487c8`.
Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

The bounded comparison executes the entire original routine, its real CRT power
helpers, environment helper and RPM helper. It compares owner/configuration
bytes, numerics, call order and arguments. The corpus includes disabled/idle/
coasting/full-throttle paths, gain boundaries, pulse priority, boost eligibility,
loss/upgrade thresholds, all final damage paths, environment variants and child
mutations. Native/Python comparisons reuse those scenarios with strict floating
point compilation.

The original comparison passes **1,094 cases with zero error**; the optimized
Windows native build matches the same Python corpus with zero error. Run:

```powershell
python -m tools.engine_torque_update_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m tools.native_engine_torque_update_compare build/native-check/mco_engine_torque_update_compare.exe
```

Remaining supplied boundaries are `0x4b7170` (pulse), `0x549580` (boost producer),
`0x55cfc0` (query), `0x54d250` (RPM limit), `0x5452c0` (damage) and `0x591180`
(effects). Their implementations, asset/catalogue producers and live integrated
driving remain separate recovery work. The default interface rejects nonfinite
inputs, singular capacity and out-of-envelope catalogue arithmetic. It requires
explicit callbacks and does not silently replace unknown children.
