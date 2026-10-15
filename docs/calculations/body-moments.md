# Wheel-force transformation and body moments

These authored Python/C++ calculations reproduce complete original `0x540520`
and `0x540710`, including its actual `0x540600` correction and cross-product
helper. They are force consumers, not a complete vehicle integrator.

Source: x86 `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Evidence: force accumulator
`ev_562052f2f87aabaa33b332a4e182eba57b808636146ddf65da5b6e41c51528ab`,
correction `ev_c6536455188181a143d32e4f7cb7cd64f3bf18b3acfdd313cd21caf225667262`,
orientation `ev_d55222757ac60a3e9ef9e031707b19e80f051b3147caca889bada8fb30d7b4c2`.
Original code and raw research captures remain external/private.

## Force orientation

For consecutive wheel slot `i`, supplied phase `p`, steering `s` and axle
parameter `a`, the original stores a float32 phase `i/4 + p` and angle:

```text
angle = s + sin((i/4 + p) × float32(2π)) × a × float32(0.044444445)
```

Angles use turns. Axle parameters come from owner `+0xd08` and `+0xd0c`, phase
from wheel `+0xf4`; their component/world producers remain unresolved. The
original then transforms lateral `L` and longitudinal `D` outputs as follows:

```text
new_L = L - sin(angle × float32(2π)) × D
new_D = float32(cos(angle × float32(2π))) × D - sin(angle × float32(2π)) × L
```

Each output is stored float32. The first expression retains `L` directly;
substituting a conventional rotation matrix would change verified behavior.
For zero axle parameter, steering a quarter turn and forces `L=100,D=200`,
the outputs are approximately `−100,−100`.

## Body moments

Consecutive records are consumed in order `0,1,3,2` for cross products. Their
positions use front half-track signs `−,+` and rear signs `−,+` in that order;
longitudinal arms are the front lever and negative rear lever. Height is
configuration `+0x38 × float32(0.9090909)`. Front/rear vertical contributions
are supplied owner `+0xbdc/+0xbe0`, not assumed to be individual wheel loads.

Yaw combines front lateral forces times the front lever, minus rear lateral
forces times the rear lever, a separate supplied yaw contribution, and the
left/right longitudinal-force differences times half-track. Alternate mode
omits only this last differential longitudinal contribution. The result is
scaled by the supplied inverse-yaw parameter and turn conversion; secondary
wheel responses add another yaw term. Original float stores are retained.

Below absolute speed `0.5`, pitch and roll are zeroed while yaw remains. At
speed `0.5` and above, each original `force × position` cross product produces:

```text
pitch_contribution = vertical_force × longitudinal_arm - longitudinal_force × height
roll_contribution = lateral_force × height - vertical_force × lateral_arm
```

Cross-product outputs and running sums are stored float32 per original calls.
Pitch is scaled by inverse pitch, a separate pitch multiplier and turn
conversion; roll by inverse roll and turn conversion. The final helper adds
support-related corrections for each contacting wheel with nonzero wheel
`+0x74`:

```text
quarter_mass = float32(configuration_mass × 0.25)
c = float32(quarter_mass × wheel_support_correction)
pitch += c × positive_axle_lever × inverse_pitch × float32(1/(2π))
roll += c × axle_half_track × inverse_roll × float32(1/(2π))
```

It adds positive axle arms in both front and rear branches; do not invent
left/right signs or reinterpret this field as a normal-load value. Its producer
and physical units remain required. The returned three moments retain neutral
calculation units until the full downstream integration is recovered.

## Verification and remaining integration

```powershell
python -m tools.body_moments_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m tools.wheel_force_orientation_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m tools.native_driving_compare build/native-check
```

The full accumulator passes 1,440 bounded original cases with maximum absolute
error `1.1920928955078125e-7` and no substituted calls. Cases include adjacent
speed gates, force and correction signs, all contact masks and alternate mode.
The orientation passes 243 original cases exactly, using actual trigonometric
helpers. Both native ports match their Python corpora exactly. Full owner and
configuration images are checked for unexpected writes.

The [gear-bound driving comparison](gear-binding.md) additionally exposed two
premature float32 stores in lateral/extra yaw contributions. Both remain on the
original x87 stack through primary yaw accumulation. Python and C++ now retain
those intermediates, preventing carried yaw drift in that integrated corpus.

Tolerance is `max(0.00025, abs(original) × 3e-7)`. These comparisons use supplied
state; they do not establish authentic-car parameter production, aerodynamic
forces, local/world transforms, tick scheduling or integrated linear/angular
velocity traces. Those stages remain separate gates before playable replacement.
