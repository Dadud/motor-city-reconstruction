# Control smoothing and dispatch

`0x540fd0` updates throttle/brake bytes, signed steering, gear child dispatch,
emergency overrides and normalized controls. It does not calculate aerodynamic
forces. The Python and C++ implementations preserve its arithmetic and ordered
child interfaces. Evidence:
`ev_8a5eb25f92d438b4200c94ae31d6602e9ecba2d54204f27a9e9415af11bc8990`,
verified executable SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

## Inputs and stages

| Owner field | Reconstructed meaning |
| --- | --- |
| `+0xa60`, `+0xa61`, `+0xa62` | Target throttle, brake, gear bytes |
| `+0xa63`, `+0xa64`, `+0xa65` | Throttle, steering, brake smoothing flags |
| `+0xa66`, `+0xa67` | Current throttle/brake bytes |
| `+0xa78`, `+0xa7c` | Target/current signed steering |
| `+0xa6c` | Special slow steering control |
| `+0xa87` | Emergency flag |
| `+0xa8c`, `+0xa90`, `+0xa94` | Normalized steering, brake, throttle |
| `+0xae4` bit 2 | Set when normalized throttle decreases |

The initial remote-control flag query (`0x43b570`) tests owner `+0x474` bit
`0x200`. If set, the remote-control child `0x548670` executes before smoothing.
The reconstruction requires a child executor; it supplies no runtime no-op or
invented remote input. After smoothing, configuration `+0x68c` selects the
assisted (`0x548b70`) or manual (`0x548e30`) gear child. These complete gear
functions remain external effects, including any state mutations they perform.
The control routine then runs the recovered override helper `0x541880` and
produces normalized outputs. Diagnostic trace delivery is an explicit final
effect, with its original two numeric arguments.

## Per-player rate scaling

The three original rate helpers `0x541400`, `0x5414a0`, `0x541540` compare owner
`+0x464` with the supplied local-player identity. For other owners they return
the unscaled rate. For the local player:

`factor = clamp(float32(unsigned_setting / 256 + 0.5), 0.5, 1.5)`

`rate = max(1, nearest_even(float32(factor * integer_rate)))`.

Settings are unsigned 32-bit values. Configuration steering rates are first
stored as float32 and converted to integer using nearest-even rounding. The
authored C++ API performs this conversion explicitly, independent of the host's
ambient rounding mode. For example, configuration `2.5` becomes 2 and `3.5`
becomes 4 before local-player scaling.

## Throttle and brake

Throttle smoothing uses independently scaled base attack 8 and release 16.
Let `difference = target - current`:

- Differences of at least 32 move by `min(attack, difference)`.
- Positive differences 2–31 move by `min(attack / 2, difference / 2)` using
  integer truncation; a difference of one moves exactly one.
- Differences of at most -32 move by `min(release, -difference)` toward target.
- Negative differences -31 through -2 use the corresponding half-rate rule;
  a difference of -1 moves exactly one.
- Zero holds; disabling smoothing copies the target byte directly.

At current throttle 100, targets 131 and 132 therefore produce 104 and 108
with default unscaled rates. Target 68 instead produces 84. The discontinuity
at 32 is observed behavior, not an interpolated response curve.

Brake smoothing immediately follows a decreasing target. An increasing target
adds the scaled base rate 10, then caps at target. The local player additionally
applies its supplied brake limit clamped to `[0,255]`. Disabling smoothing copies
the brake target and bypasses this smoothed-path limit.

## Two steering algorithms

Global mode `0xa38494` selects two distinct algorithms, preserved separately.

In the newer mode, disabled smoothing directly copies target steering without
the smoothed path's `[-127,127]` clamp. With smoothing enabled, a zero target
returns toward zero using configuration `+0xf0`, except that special slow
control holds current steering. A nonzero target moves toward target using
configuration `+0xf4`; special slow control replaces its computed rate with 2.
The smoothed result is clamped to `[-127,127]`.

The legacy helper `0x5415e0` instead clears steering to zero for a sign reversal
before responding on the next call. A zero target returns using configuration
`+0xf4`. Otherwise it uses `+0xf0` and alters rate according to current steering
and direction: double within the central 32-unit region, unchanged through 64,
half through 96, quarter beyond 96. The exact signed comparisons are retained.
For example, increasing positive steering from 96 with rate 8 moves by 4;
from 97 it moves by 2. Disabled legacy smoothing still ramps by at most 32 per
call. Both legacy paths clamp to `[-127,127]`.

These are per-call increments. This routine does not establish the original
input sampling rate, and the port does not introduce a frame-time multiplier.

## Overrides and normalized values

The recovered override helper first checks the emergency flag, otherwise a
supplied stopped-state query (`0x584fc0`). An override requests the original
virtual operation 1. A true result clears target/current steering; a false
result sets the reverse-control byte. Both outcomes clear throttle and its
target, clear the auxiliary-control byte, set target/output gear to one, and
set brake to 192. If neither emergency nor stopped-state override applies, a
false supplied vehicle-gate query (`0x55cfc0`) instead sets brake to 255.
External query implementations and the virtual receiver remain unresolved;
the public executor must supply explicit boolean observations.

With `k = float32(1 / 255)`:

- Throttle output is `clamp(float32(throttle_byte * k), 0, 1)`. A decrease
  compared with the previous output sets flags bit 2; equal/increased clears it.
- Let extended `x = brake_byte * k` and stored `b = float32(x)`. Brake output is
  `clamp(float32(x * b * 0.5 + b * 0.5), 0, 1)`.
- Steering output is `float32(signed_steering * float32(1 / 127))`.

The byte product's retained precision in the brake square is deliberate.
Trace delivery receives stored `b` and the computed brake output before the
owner brake-output field is updated. The owner store after trace delivery is
preserved even if the supplied delivery executor mutates that field.

## Verification and remaining work

`tools.control_update_oracle` executes 844 complete original calls with all
original scaling helpers, both steering algorithms, integer clamping and
override helper instructions. Only remote/gear child effects, external query
boundaries and trace delivery are supplied. Each supplied child entry captures
the complete owner image and compares it against the Python state before that
child effect. Consequently the supplied gear effect's brake mutation cannot
hide an incorrect earlier brake ramp. Ordered calls, virtual operation/receiver,
trace arguments, final owner bytes and unchanged configuration are checked.
Maximum absolute error is zero. The same 844 scenarios pass exact native/Python
state and ordered-call comparisons.

The corpus covers both modes, smoothing flags, local/other players, uint32
setting extremes, steering thresholds/sign changes, throttle ±1/±2/±31/±32/±33
differences, slow steering and all emergency/stopped/override/gate/remote
combinations. Ten Python tests and one native behavioral executable separately
check rates, boundaries, repeated reversal, nearest-even conversion, overrides,
callback order and invalid/missing child behavior.

Authentic input acquisition, remote input production, complete assisted/manual
gear state machines and external emergency/vehicle queries remain incomplete.
The diagnostic formatter itself is not emulated. This establishes the numeric
consumer and child interface, not a finished playable input/gear system or a
live original-client comparison. Original executable bytes and private
decompiler output remain outside the public source.
