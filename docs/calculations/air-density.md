# Air density from altitude and weather

The authored Python/C++ calculation reproduces the float32 density consumed
by the original body resistance stage. `0x535ed0` computes the density;
`0x594030` selects the weather code and `0x69a630` supplies the floor operation.

Evidence: `ev_25b9391114a2f48d6d4451a50d31777ffcd314c91684f267079c3c6013170511`
and `ev_7d43940470aa755c59b269f6dc6a598061d619684bbaa0882bcc121d3f0b52fd`.

## Table and interpolation

The input is the owner's altitude field `+0x34c`. The routine stores
`shifted=F32(altitude+500)` and computes
`index=floor(shifted×F32(0.002))`. Adjacent table entries are interpolated
at 500-unit intervals:

| Index | Density |
|---:|---:|
| 0 | 1.347 |
| 1 | 1.2849 |
| 2 | 1.225 |
| 3 | 1.1673 |
| 4 | 1.1117 |
| 5 | 1.0581 |
| 6 | 1.0066 |
| 7 | 0.95695 |
| 8 | 0.90925 |
| 9 | 0.8634 |
| 10 | 0.81935 |
| 11 | 0.77704 |
| 12 | 0.73643 |

Table entries and constants are original float32 values, not ideal decimal
values. The returned extended value is stored to float32 by its consumer.

```
interpolated = table[index]
             + (table[index+1]-table[index])
             × (shifted-index×500) × F32(0.002)
density = F32(interpolated × F32(288.15) / temperature)
```

Temperature starts at float32 288.15, or 278.15 when the cold-environment
global is nonzero. Weather selection returns zero unless its global gate
is enabled. Selected weather code 1 subtracts 10 from temperature; code 2
subtracts 20; other codes leave it unchanged. Each temperature update stores
to float32. Altitude zero selects table entry 1, about 1.2849 before temperature
adjustment. This observed offset is retained even though table entry 2 is
the familiar 1.225 standard-air value.

The names density and temperature describe the equation and constants.
Authentic altitude units, environment flag producers and weather settings
still require track/configuration and runtime corroboration.

## Verified domain and execution

The public API accepts table intervals with indices 0 through 11. Out-of-range
indices are rejected; the original has no bounds check and would read local
stack data beyond its thirteen initialized density entries. The index-12
upper interpolation neighbor also aliases a temporary floor-result slot,
so no extrapolated atmosphere is invented for that interval.

`tools.air_density_oracle` executes the complete density routine, real weather
selector and real floor helper, without substitutions. All 260 cases match
the consumer's float32 value exactly, including table-boundary neighbors,
cold/warm flags, enabled/disabled weather and weather codes 0,1,2,3 and the
maximum unsigned code. The full owner image is checked for unexpected writes.
The native corpus matches Python exactly.

The connected body-resistance comparison also executes this producer on the
same original owner rather than supplying a density constant. See
[body resistance](body-resistance.md) for its remaining wind/drafting boundary.
