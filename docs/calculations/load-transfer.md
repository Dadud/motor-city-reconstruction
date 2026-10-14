# Acceleration-driven wheel load transfer

The complete original helper `0x53e680` adjusts four existing normal loads using
local accelerations, attitude, speed and component parameters. It is implemented
in `client/load_transfer.py`. This helper consumes initial loads; it does not
compute contact, static suspension loads or a complete wheel-force update.

## Original inputs and order

The processing order is LF, RF, LR, RR at owner offsets `0x6d0`, `0x7dc`,
`0x9f4`, `0x8e8`. Owner `+0xa38` and `+0xa30` supply longitudinal and lateral
acceleration values after the enclosing update's local-coordinate transform.
Owner `+0xa2c` supplies speed. The helper skips corrections when the absolute
attitude value at `+0xc00` exceeds 0.25; equality remains active.

The component record supplies mass, wheelbase and front/rear track dimensions.
Its `+0x38` parameter is multiplied by the executable's float32 `0.9090909`
and stored as float32; call this converted value `h`. Its full physical meaning
and the two owner axle offsets at `+0x18ec`/`+0x18f0` remain under investigation.
The API uses `height_parameter`, `front_offset` and `rear_offset` to keep those
observed inputs explicit.

If absolute longitudinal acceleration exceeds float32 `0.1962`:

```text
c = float32(-longitudinal_acceleration × (h / wheelbase) × mass × 0.5)
LF = max(0, float32(LF + c))
RF = max(0, float32(RF + c))
LR = max(0, float32(LR - c))
RR = max(0, float32(RR - c))
```

The lateral correction runs only when absolute lateral acceleration exceeds the
same threshold and absolute speed exceeds 6. Both comparisons are strict.
Importantly, it reads the axle sums **after longitudinal correction and clamping**.
Both lateral corrections are computed before either axle's new loads are written:

```text
front_c = float32((LF + RF) × float32(0.101936795) ×
                  ((h - front_offset × float32(0.8)) × lateral_acceleration / front_track))
rear_c  = float32((LR + RR) × float32(0.101936795) ×
                  ((h - rear_offset × float32(0.8)) × lateral_acceleration / rear_track))

LF = max(0, float32(LF + front_c))
RF = max(0, float32(RF - front_c))
LR = max(0, float32(LR + rear_c))
RR = max(0, float32(RR - rear_c))
```

These are the recovered constants and operations, not an inferred generic vehicle
formula. Individual zero clamps can change the total load; the reconstruction
does not renormalize it. The authored API validates finite float32 observations,
nonnegative initial loads and positive mass/dimensions. These safeguards are not
original error handling.

## Verification and limits

Target `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA dossier: `ev_e3bc9bdc0a22a551ca6e71e8f6a44f618fd882b757ace365c3b937c0253a9159`.

```powershell
python -m tools.load_transfer_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
python -m unittest tests.test_load_transfer
python -m tools.native_load_transfer_compare build/native-check/mco_load_transfer_compare.exe
```

The local Windows bounded oracle matched 1,250 complete original-function cases
with zero maximum difference in stored loads. No calls are substituted. It checks
all four loads and every other owner/configuration byte for unexpected mutation.
The corpus covers both attitude signs and exact 0.25 boundaries, both acceleration
signs and exact thresholds, both speed signs and exact 6 boundaries, and load
clamp crossings. Four focused tests cover gates, signs, original wheel order and
invalid observations. The numeric comparison allows
`max(0.00025, abs(original)×3e-7)`; this corpus is exactly equal.
The C++20 port matches all 1,250 Python corpus cases exactly. Its native unit
check and comparison run in Windows/Linux CI; local verification was on Windows.

Initial normal-load production, support masks, the following `0x53e980` correction,
component semantics and enclosing timestep scheduling remain required. The
[driving recovery map](../driving-recovery-map.md) records their research paths.
