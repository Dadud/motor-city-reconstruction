# Wind, drafting and connected body resistance

The Python/C++ implementations recover the complete numeric wind function
`0x536fb0` and drafting function `0x536960`. The connected
`calculate_body_environment` executes air density, wind, drafting and
[body resistance](body-resistance.md) in their original order. Track data,
simulation counter, mode observations, vehicle geometry and component fields
remain explicit inputs; authentic production of all those inputs is not proved
by these comparisons.

## Wind

The original reads the selected track's three-vector and uses its X/Z values
to compute a heading with `atan2(X,Z)`. A virtual query `(1,0)` can disable
wind, returning a zero vector and false. Otherwise, with `F32` marking stores:

```
t = F32(simulation_counter / 64)
p = F32(t * F32(0.033333335))
q = F32(t * F32(0.026666667))
s = sin(p * tau) * F32(sin(q * tau))
offset = F32(signed_remainder(weather_seed, 360) * F32(0.0027777778))
heading = F32(atan2(track.X, track.Z) * inverse_tau + offset)
heading = F32(s * F32(0.055555556) + heading)
base = clamp(signed_remainder(weather_seed, 15), 3, 15)
magnitude = F32(base * F32(0.44703) + s * F32(1.117575))
world.X = F32(sin(heading * tau) * magnitude)
world.Y = 0
world.Z = F32(cos(heading * tau) * magnitude)
```

`tau = 6.2831854820251465` and `inverse_tau = 0.15915493667125702`
are the original double constants. The resulting vector is transformed by the
owner's row-vector matrix at `+0x9c`, with original addition order and one
float store per output. A tilted matrix can produce a vertical component.
The body-resistance caller consumes X and Z. The return flag tests the
untransformed stored magnitude, not the transformed vector's length.

Signed remainder truncates division toward zero, so `-361 % 360` is `-1`
in this calculation. Python's ordinary remainder would select a different
strength for negative seeds. Counter zero, seed zero, track direction `(0,0,1)`
and identity matrix give approximately `(0,0,1.34109)`. The constants resemble
speed conversions, but units and counter production still need corroboration.
Dividing the counter by 64 does not independently establish scheduler timing.

## Drafting

The original scans the ordered vehicle list and skips itself. A candidate is
eligible when horizontal X/Z distance is at most six times the current car's
Z half-extent and the raw forward-vector dot product is at least stored
`0.9659258`. The dot product is not normalized by this routine. The first
eligible car determines the result, even when another car is closer or offers
a stronger wake.

For that candidate, the routine constructs four rear-facing corner vectors
using its basis and half-extents. Adjacent corner cross products become four
unnormalized wake-plane normals. It also stores the wake origin at the
candidate's position plus three Z half-extents along its forward vector.
These are writes to the **candidate car**, not temporary local-only geometry.

The current car's sample point is its position plus one own Z half-extent
along its forward vector. All four plane dot products with the sample-to-wake
relative vector must be nonnegative for the inside branch. Let `L` be the
current car's Z half-extent, `reach = F32(6*L)`, `d` the stored horizontal
distance and `a` the stored alignment:

```
inside factor = F32(((F32(1.0340742) - a) * (d + reach) * 0.25)
                    / (reach * F32(0.034074187)))
outside factor = clamp(F32((L/d)*0.25 + 1), 1, 1.25)
```

No eligible candidate returns one without wake writes. The inside result is
not subsequently clamped by this routine. Coincident horizontal positions in
the outside branch produce positive infinity in original x87 division; its
clamp returns 1.25. The authored implementation handles this case explicitly.
For aligned cars, `L=2`, distance four and a sample inside the wake, the factor
is approximately one third. The outside branch can increase resistance.

The comparison preserves cell-specific storage: some corner products remain
unstored until addition/subtraction, while others have already been rounded.
Each cross-product component stores once. Replacing these steps with a generic
float-only geometry pipeline changes wake fields near boundaries.

## Shared-state integration and verification

`client/body_environment.py` and `native/src/body_environment.cpp` connect
the recovered producers to body resistance. Original stored density, wind X/Z
and drafting factor replace stale values in the supplied body record. The
result includes density, wind, body outputs and all vehicle records carrying
the selected peer's wake writes. The caller must retain those records.

- Wind: 5,760 complete original calls, actual atan/sin/cos helpers; only the
  external virtual mode query is supplied.
- Drafting: 865 complete original calls with all numeric helpers; self, range,
  alignment, inside/outside, ordered-list and cross-car writes are checked.
- Connected environment/body: 432 complete original body calls with actual
  density/weather, wind, drafting and numeric helpers. Only the wind mode
  query is supplied. Full current/peer car images and producer order are checked.

All observed output errors are zero in these corpora; native/Python comparisons
also match. These are bounded original-instruction comparisons, not observed
live driving or an online race acceptance run. Other forces, contact creation,
engine/tire state, component effects and original-asset input assembly still
need to be connected into a complete driving tick.

Run `python -m tools.wind_oracle <mcity.exe>`,
`python -m tools.drafting_oracle <mcity.exe>` and
`python -m tools.body_resistance_oracle <mcity.exe> --actual-environment`.
The verified executable identity is recorded in [the driving map](../driving-recovery-map.md).
Wind evidence: `ev_1c681e02ee96a9a577bee07dc14fb928efc098bf4d1ea887f454199c091a237b`.
Drafting evidence: `ev_90a4c541917d34ad15b8c9c5b3a57f0df6d16592482596a10d58b21306debf11`.
