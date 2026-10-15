# Body vertical contributions and wheel loads

The recovered `0x536250` stage computes two axle vertical contributions from
longitudinal speed, then adjusts the four existing wheel normal loads. The
`0x536f80` helper selects the rear parameter. This is authored behavior,
not restored original source.

Evidence: `ev_869a5b7d253052ccb4e7e1b21b13e501ab2103f4f039ac527030e0be30a5d784`
and `ev_a20801cd3011d70f718dfb4582f14d53d131bb588dd8e66c6e87038ba4135b84`.
Execution uses the verified local executable identity recorded by
`tools.native_oracle`; it does not launch the game's entry point or services.

## Inputs and calculation

The owner supplies speed at `+0xa2c`, longitudinal speed at `+0xa44`,
axle adjustments at `+0xd30/+0xd34`, and axle quality parameters at
`+0xd18/+0xd1c`. Configuration supplies axle parameters at `+4/+8` and
additional parameters at `+0x410/+0x420`.

When signed speed is at least float32 `8.9406`, add the additional parameters
to the base axle parameters. Reverse motion does not select this branch.
For each axle with a nonzero adjustment, multiply its parameter by
`1-adjustment` if the parameter is nonnegative, or `1+adjustment` otherwise.

With `F32` denoting a float32 store:

```
scale = abs(longitudinal_speed) × F32(4.905)
front_vertical = F32(scale × adjusted_front_parameter)
rear_vertical = F32(scale × adjusted_rear_parameter)
wheel_load = max(0, F32(old_load + (1-axle_quality) × axle_vertical))
total_vertical = F32(front_vertical + rear_vertical)
```

The scale product remains extended until the axle contribution is stored.
Negative axle contributions are permitted; wheel loads are then clamped at
zero. Quality values are not clamped by the original routine.
Consecutive wheel records map to offsets `+0x6d0/+0x7dc/+0x8e8/+0x9f4`;
the original writes rear records in order 3 then 2. Outputs also populate
`+0xbdc/+0xbe0/+0xbe4`.

For longitudinal speed 2, front parameter 1, no adjustment and quality 0,
the front contribution is about 9.81; a front wheel initially loaded at 100
becomes about 109.81. The parameter's physical dimension remains unresolved;
the constant alone does not prove that this is a conventional aerodynamic
lift equation.

## Verification and limits

`tools.body_vertical_load_oracle` executes the complete original function and
rear selector without replacing calls. Its 486 cases cover threshold
neighbors, reverse motion, both speed signs, signed/zero parameters,
adjustments, qualities and clamped loads. Every recorded output matches
exactly; the complete owner and configuration are checked for unexpected
writes. Python and C++ retain the same explicit stores.

Authentic configuration, damage/quality and wheel-load producers still need
integrated verification. These bounded comparisons do not demonstrate
complete car handling or original-client runtime behavior.
