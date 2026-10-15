# Body resistance and load transfer

The authored Python/C++ stage reproduces the arithmetic of `0x536480`.
It consumes explicit air density, body-space wind and drafting values.
Their original producers are identified. [Air density](air-density.md) is
independently recovered and also runs in a connected comparison; wind and
drafting remain explicit supplied boundaries.

Evidence: `ev_7b505cd5ecf57d905f56a857dcc2b33e116558ea1eed4974c140cdc42c219159`.
Producer evidence: air density
`ev_25b9391114a2f48d6d4451a50d31777ffcd314c91684f267079c3c6013170511`,
wind `ev_1c681e02ee96a9a577bee07dc14fb928efc098bf4d1ea887f454199c091a237b`,
drafting `ev_90a4c541917d34ad15b8c9c5b3a57f0df6d16592482596a10d58b21306debf11`.

## Drag, side force and moment

Start with the configuration drag parameter. If both the configuration
accessory flag and owner accessory flag are enabled, add float32 `0.02`.
For nonzero owner drag adjustment, multiply by `1+adjustment/2`.

The secondary-angle multiplier is limited according to the signed vehicle code:

| Code | Multiplier rate | Multiplier maximum | Lateral coefficient |
|---|---:|---:|---:|
| 6 | 0.003 | 1.12 | 6 |
| At most 3 | 0.0125 | 1.5 | 10 |
| Other | 0.006 | 1.24 | 8 |

Multiply the secondary angle by 180, store it, then take its absolute value.
The multiplier is `min(maximum, F32(1+abs(stored_angle)×rate))`.
Let `u=F32(abs(speed)-wind_longitudinal)`:

```
drag = F32(u² × density × area × multiplier × drag_parameter × 0.5)
drag = F32(drag × drafting_factor)
yaw_contribution = F32(wind_lateral² × lateral_coefficient × density × area × signed_half)
moment = (height × F32(0.9090909) + sin(pitch_turns × F32(6.2831855)) × length) × drag
```

`signed_half` is -0.5 for negative lateral wind, +0.5 otherwise. The original
drag output is negative when longitudinal speed is nonnegative, positive
otherwise. The moment calculation uses the positive drag magnitude.
The resistance-disabled flag clears drag and stored moment; lateral wind
still contributes. A supplied drafting factor is applied after the first
drag store, not before it.

## Wheel-load effects

Unless the owner's short load-transfer mode is nonzero, halve the unrounded
moment. Subtract its front-lever quotient from both front loads; add its
rear-lever quotient to the rear loads. Clamp each stored result at zero.
The original retains intermediate precision for the first rear addition
and uses its stored quotient for the second.

If all four wheel contact flags are set, additionally apply
`(owner_downforce+configuration_downforce) × u² × density × area × -0.5 × 0.25`
to each load. The first front addition retains the product before storing;
subsequent additions use the stored product. This extra contribution does
not use the angle multiplier or drafting factor. Negative downforce
parameters may increase loads. The original does not impose modern
coefficient validation or a replacement aerodynamic model.

For zero angle, drag parameter 0.4, relative speed 17, density 1.225,
area 2.2 and drafting factor 0.75, drag magnitude is about 116.827.
Vehicle-code multiplier branches, accessory and adjustment parameters can
change that result. Units of every catalogue parameter still require
producer and runtime corroboration.

## Comparison boundary

`tools.body_resistance_oracle` runs the entire original arithmetic stage and
original sine helper. It supplies only `0x535ed0` (density), `0x536fb0`
(wind) and `0x536960` (drafting), checking their receiver and call order.
432 cases cover forward/reverse/zero speed, all coefficient branches,
both secondary-angle signs, contact patterns and both disable flags.
The corpus currently matches all outputs exactly and checks complete
owner/configuration images for unexpected writes.

With `--actual-density`, another 432 cases run the real density, weather and
floor functions on the same owner across altitude/environment combinations.
Only wind and drafting remain supplied. This does not verify those two
producers. Wind depends on track configuration, global time and
a virtual mode query. Drafting scans nearby vehicles and mutates wake
geometry on those vehicles. The complete game still needs those producers
and integrated force/pose execution with real cars and tracks.

The C++/Python corpus includes both sets, 864 cases total, with zero observed
error. The public calculation inputs retain explicit density so callers can
use the recovered atmosphere without tying body forces to platform globals.
