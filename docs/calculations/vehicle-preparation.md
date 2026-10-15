# Vehicle orientation preparation and support disturbance

The reconstructed preparation stage implements the complete numeric behavior of
`0x54ebe0`. The support stage implements complete `0x427da0`. Both have Python
and C++ ports. They consume observed owner/configuration state; they do not read
keyboard/controller input or generate collision contacts.

Evidence: `ev_e4f3464e1ef1d1cb378029ff40fc1ec4a8efa79f56af0d584fde5f8acc76d2ae`
and `ev_c096634f98dce99edae7503cecd3ab531e35807eda1a9e8f2bc625c8a4a57b13`,
from the verified executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Static observations establish calls and storage; bounded execution independently
checks authored equations against the complete original instructions.

## Preparation

The first output is a damping scalar at owner `+0xc0c`. Its branch uses local
vertical acceleration at `+0xa38`. Positive acceleration chooses the rear
observation `+0xd2c` and configuration factor `+0x10c`; negative acceleration
chooses front `+0xd28` and configuration `+0x108`. Zero leaves the scalar at one:

`damping = clamp(1 - (1 - observation * 0.5) * factor, 0, 1)`.

The support count at `+0xc08` determines the second branch. Counts of two or more
clear the three angle deltas, retain the current angles/extent and six auxiliary
values, and still rebuild both orientation matrices. Counts below two clear the
six auxiliary values and smooth the angles/extent before rebuilding matrices.
This distinction matters in connected updates: the clear is conditional.

The supplied matrix at `+0x78` contains three independently consumed elements:
`+0x7c`, `+0x88`, `+0x94`. The authored API verifies that the named observations
match those elements; they are not separate tunable values. Another matrix at
`+0x9c` transforms the vector at `+0x328` using a row-vector product. All three
transformed coordinates are stored as float32.

Let `scale = clamp(matrix[4], 0, 1)` and `k = 0.15915493667125702`.
The original atan helper computes `atan2(first argument, second argument) * k`:

- `p = float32(atan2(matrix[1], abs(matrix[4])) * k * scale)`.
- `r = float32(atan2(matrix[7], abs(matrix[4])) * k * scale)`.
- Owner `+0xc00 = float32(r - atan2(transformed.z, transformed.y) * k + offset)`.
- Owner `+0xc04 = float32(p - atan2(transformed.x, transformed.y) * k)`.

The two last fields are observations, rather than the targets directly used by
the smoothing below. The pitch target is `r` clamped to
`[-minimum_pitch, maximum_pitch]`. The roll target is `p` clamped symmetrically
to `maximum_roll`. The extent target is the maximum of:

- `abs(float32(sin(roll * tau) * pitch_extent))`.
- `abs(float32(sin(pitch * tau) * roll_extent))`.
- `float32(scale * max(pitch_limit, roll_limit) * float32(0.66))`.

`tau = 6.2831854820251465`, the original double constant. For each of pitch,
roll and extent the routine stores `delta = float32((target - old) / 64)`.
It then adds the delta and clamps the result to the corresponding bounds;
extent uses `[0, max(pitch_limit, roll_limit)]`. The factor is per call and does
not itself establish a scheduler frequency. Angles are consumed as turns by
these original sine/cosine helpers.

For example, an old pitch of `-0.2` and a target of zero first produce a delta
of `0.003125`, then an unclamped new value near `-0.196875`. A lower limit of
`-0.06` changes the final stored pitch to the float32 representation of `-0.06`.
The delta remains the pre-clamp delta.
The pitch addition retains the extended delta after storing it; roll and
extent reload their float32 deltas. The ports preserve that distinction.

The routine builds the X-axis pitch matrix and Z-axis roll matrix, multiplies
pitch × roll × supplied matrix, and stores the transpose as the inverse-facing
matrix. It does not compute a general matrix inverse. The reconstruction keeps
the original matrix helper's cell-specific addition order and float32 stores.
Supplied matrices need not be orthonormal in the bounded comparison corpus;
that corpus checks arithmetic rather than establishing authentic matrix inputs.

## Support disturbance

The controller's previously named `support_bookkeeping` stage changes physical
wheel state. For each consecutive wheel, contact at `+0xec` gates the outputs:
displacement `+0xf0` and correction `+0x74`. Missing contact clears both.
The bound observation is `+0xb8`, not normal load `+0xd4`. Its physical units
and original producer remain unresolved; the API calls it `bound_parameter`.

The wheel's surface class selects an amplitude and frequency from the original
pair table at `0x97c238`. The reconstruction requires these coefficients and
the 256-byte lookup table at `0x890724` as supplied inputs. Original table data
is not redistributed or replaced with invented noise.

For a contacting wheel:

1. `cycle = float32(owner_phase * frequency)`.
2. Convert cycle to signed integer with nearest-even rounding. Add one for
   rear records 2 and 3, then mask to eight bits for the lookup index.
3. `noise = float32(lookup[index] / 128 - 1)`.
4. `speed_factor = float32(local_longitudinal_speed * frequency * float32(tau))`.
5. Compute `disturbance = noise * amplitude * sin(cycle * tau)` and
   `velocity = disturbance * speed_factor` with retained extended products.
6. `displacement = float32(old_displacement + velocity / 32)`, clamped to
   `±min(float32(bound_parameter / 4), abs(float32(disturbance)))`.
7. `correction = float32(float32(velocity) * speed_factor)`.

The correction has two speed factors, while the displacement increment has
one. Reversing the longitudinal speed reverses the displacement increment and
preserves correction for otherwise equal inputs. Zero speed clears correction
but can retain a bounded previous displacement. The original rounding mode is
part of the conversion contract; the C++ port implements nearest-even directly
instead of inheriting an unrelated host rounding mode. The authored API rejects
cycle conversions outside signed int32 and negative bound observations.

## Verification and limits

`tools.vehicle_preparation_oracle` checks 251 complete preparation calls and
384 complete support calls. The preparation corpus covers all five support
counts, positive/zero/negative acceleration, orientation scale below/inside/
above bounds, angle clamp boundaries, retained fields and matrix outputs.
Support covers all sixteen contact masks, forward/stationary/reverse motion,
negative and wrapping cycles, distinct per-wheel coefficients and byte lookup.
Full owner bytes are checked; configuration and byte lookup are checked for
unexpected writes. All original atan, sin, cos, matrix multiplication and
transpose helpers execute. No original numeric helper is replaced.

Maximum absolute error is zero across this corpus. The C++/Python comparison
also returns zero over the same 635 cases. Ten Python behavioral tests and
one native behavioral executable check retained state, repeated updates,
direction, clamps, transpose layout, missing contact and invalid supplied input.
The retained-pitch regression uses an old pitch of `-0.0020816968753933907`
and a clamped target of float32 `-0.06`: the original returns
`-0.0029866702388972044`. Reloading the stored delta returns
`-0.002986670471727848`, one float32 ULP away. Both ports check the original
answer directly rather than merely accepting this error within a tolerance.
The comparison tolerance is `max(0.000003, abs(original) * 0.0000004)`; the
zero observed error is a corpus result rather than a universal identity claim.

Remaining work includes authentic source vector/matrix production, surface
table/lookup initialization, phase production and its timing, the bound
observation's units/producer, and handoff of support correction to downstream
load/moment stages in a complete original caller tick. These tests are CPU-only
bounded execution, not live original-client driving or fan-server verification.
