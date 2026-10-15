# Engine startup and driving dispatcher

The complete dispatcher at `0x545af0` is reconstructed in
`client/engine_update.py` and `native/src/engine_update.cpp`. Its RPM helper
`0x546e70` and torque lookup `0x548f00` execute as recovered calculations.
Other child functions require an explicit executor; no inferred clutch or torque
model is substituted. The original comparison covers 1,159 cases, including
12 supplied child-write cases, with exact output floats, integer fields,
call order and owner/configuration byte checks.

## State and decisions

The engine-enabled bit is bit zero of owner `+0xae4`. Vehicle flags at `+0x474`
select the paths below. These bit positions describe observed behavior; their
original symbolic names are unavailable.

| Vehicle flags | Observed path |
| --- | --- |
| Bit 1 clear, bit 2 set, engine enabled | Setup, controls, gear link, drivetrain loads, engagement inputs, torque update, wheel drive, finalization |
| Bit 1 clear, other cases | Return after activation handling |
| Bit 1 set, bit 2 clear | Starting/idle path or fixed RPM override |
| Bits 1 and 2 set | Torque-update child or fixed RPM override |

For an initially disabled engine, interface operation 8 returning zero enables
it immediately. Otherwise the original tests
`signed32(activation_counter - 256 + selected_delay) <= current_counter`.
The counter arithmetic wraps at 32 bits before signed comparison. The delays
are explicit inputs. Eight observed selector slots are supported; the contents
following those eight delay integers belong to other constants, so the API
does not treat them as additional delays.

In the starting path, interface operation 1 selects a counter threshold of
128 or 10. The start-acceleration child runs before that threshold clears the
acceleration input, and can change the engine-enable bit before the RPM helper
is selected. Child writes are rounded at float storage boundaries before the
dispatcher continues.

The low-motion path applies when the control gate is false and owner `+0x105c`
is below stored constant `11.17575`. The physical unit of this field remains
unverified. The eight selector fractions are
`0.7, 0.6, 0.75, 0.65, 0.55, 0.8, 0.5, 0.67`. With stored fraction `f`:

```
acceleration_input = float32(limiter_RPM * f - RPM)
throttle = clamp(float32(f * float32(1.1)), 0.5, 1)
```

It then calls the recovered [RPM helper](driving-engine-rpm.md) with the
configured idle RPM as minimum. The alternative invokes the idle-regulation
child. An active override sets RPM to nearest-even rounding of
`float32(limiter_RPM * 0.875)`, stores angular speed using `float32(0.10471976)`
and clears the acceleration output. For a limiter of 6,800 RPM, this gives
5,950 RPM. This observed mode is not used as a replacement for normal driving.

## Torque knots and power

The lookup reads adjacent supplied float knots at configuration `+0x80`,
500 RPM apart. Its index is `floor(RPM * float32(0.002))`; it does not clamp
an out-of-range index. The reconstruction requires valid adjacent knots and
nonnegative RPM instead of reading unavailable memory.

```
i = floor(RPM * float32(0.002))
T = (knots[i+1] - knots[i]) * (float32(RPM) - i*500) * float32(0.002) + knots[i]
curve_torque = float32(T)
power = max(0, float32(T * RPM * float32(0.00010471976)))
```

`T` remains an unstored intermediate until its consumers: power uses that
intermediate rather than reloading rounded curve torque. For knots 10 and 30
at 0 and 500 RPM, 250 RPM gives approximately 20.000000475 before storage.
The power constant is consistent with RPM and torque in newton metres producing
kilowatts, but source units must still be confirmed from component producers.
The bit-1 paths also store effective torque 100 and normalized RPM, then call
gear link and drivetrain loads when current vehicle bits 0 and 1 are both set.

## Evidence and remaining work

Dispatcher evidence:
`ev_f4138fe586f7a644826c3fed0bf4ac2ff952ab9063efe9cdcc51b1623111253b`.
Lookup evidence:
`ev_38e498015340681f1f22d7f40a90d90b9ad32d11cdb5642169b37851a9d4bf6e`.
Instruction-level checks preserve the actual stores and counter widths where
decompiler expressions alone obscure them. Comparisons run bounded original
instructions with actual RPM/lookup bodies, supplied other child stages and
interface observations, and private original bytes.

Full engine torque, boost, damage/temperature behavior, engagement, gear links,
wheel-drive children, authentic input producers and integrated driving traces
remain required. This dispatcher closes call ownership and mode selection;
it does not establish a complete driving engine.
