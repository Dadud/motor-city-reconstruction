# Original wheel response curves

The original active tire path calls two related 26-knot response consumers:
`0x53f630` and `0x53f830`. Their interpolation, load corrections, angle term,
surface multiplier and sign conventions are now implemented in
`client/tire_response.py`. This does not recover the complete tire update.
The tables are explicit inputs; original table data is not distributed.

## Inputs and equations

Both consumers read a native angle at wheel `+4`, a second angle at `+8`,
normal-load state at `+0xd4` and a final multiplier at `+0xf8`. The caller supplies
26 float32 knots and an angle coefficient. The exact physical meaning of the
second angle, native angle normalization and table output units remain unresolved.
The observed conversion multiplies the first angle by 180; the public research
API therefore calls it `slip_angle`, without promising radians or turns.

Let `s` be that converted angle. Set `x = min(abs(s), 25)`, `i = floor(x)` and
linearly interpolate knots `i` and `min(i+1,25)`. The last knot saturates at
25; the function does not extrapolate beyond the table. Interpolation is stored
as float32 before use.

Let `L = float32(normal_load × float32(0.00025))`. The normal primary response
uses:

```text
scale = clamp(L, 0, 1)                                      when L <= 1
scale = clamp(float32(-0.1941×L² + 1.2262×L - 0.031), 1, 2.5) otherwise
```

The observed global alternate branch first clamps `L` to `[0,3.5]`, evaluates
the polynomial without `-0.031`, and clamps the result to `[0,2]`.
Its gameplay purpose is not yet established. The secondary response ignores
that switch and uses:

```text
scale = clamp(L, 0, 1)                         when L <= 1
scale = clamp(float32(2.83×L - 2), 1, 5)       otherwise
```

Each decimal coefficient above is the executable's float32 constant. The
implemented equations retain those values rather than replacing them with exact
decimal numbers. The final response before sign selection is:

```text
angle_term = second_angle × 180 × angle_coefficient × normal_load
primary    = (scale × interpolated_knot + angle_term) × multiplier
secondary  = (scale × interpolated_knot + angle_term × float32(0.15)) × multiplier
```

The primary response negates this value when `s > 0`; the secondary negates it
when `s < 0`. Zero takes neither negation. This asymmetry is preserved rather
than assigning both outputs the same sign rule.

For an authored table with knot `i = 100×i`, native angle `4.5/180`, load 4000,
zero second angle and multiplier 1, interpolation is 450 and load scaling is 1.
The primary stored output is -450; the secondary is +450.

## Evidence and checks

Target: `mcity.exe`, x86, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA function dossiers:

- Primary: `ev_bdf154ee4eac889a49aac85fa1bd4b5cd8ab1970f6ceb5fc5b2ba9dc4db74fee`.
- Secondary: `ev_0506dca8b2ebb2a711db07d1a133c96e6dc7caea18d03f0dd6c4fc459969541d`.

```powershell
python -m tools.tire_response_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
python -m unittest tests.test_tire_response
python -m tools.native_tire_response_compare build/native-check/mco_tire_response_compare.exe
```

The Windows bounded original-function run matched 1,728 cases with zero maximum
absolute difference after final float32 storage. It executes both complete
functions and their original floor helper, with synthetic tables and isolated
wheel records. Cases include both angle signs, signed zero, fractional knots,
table saturation, zero load, both sides of load 4000, high load, second-angle
signs and both global switch values. No host callbacks or sockets execute.
The comparison allows `max(0.00025, abs(original)×3e-7)` for future corpora;
the current corpus is exactly equal at the stored output.
The C++20 port also matches all 1,728 Python corpus cases exactly. Its native unit
check and comparison are included in the Windows/Linux CI build; local execution
was on Windows.

The authored API validates finite float32 values, table length and nonnegative
load. These input rejections are API safeguards, not recovered original errors.
Original NaN, infinity and invalid-pointer behavior are outside this comparison.

## Remaining integration

The [driving recovery map](../driving-recovery-map.md) records the enclosing force
path. Original table construction, slip production, grip/surface sources, contact
gates, low-speed stabilization and combination with longitudinal forces remain
required. These helpers are not wired into the prototype bicycle model: doing so
before their inputs and force update order are recovered would invent handling.
