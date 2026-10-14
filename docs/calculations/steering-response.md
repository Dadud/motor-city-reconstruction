# Original speed-dependent steering response

`0x541930` shapes the signed steering observation used by the enclosing tire
update. `client/steering_response.py` reproduces this bounded helper. Keyboard,
controller and maximum wheel-angle producers are separate recovery work.

Source `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA Evidence:
`ev_be26071377886cb6cf69497af5927649fdcda21138cc0cb9d5e577c2858cedc8`.

## Inputs, equations and example

The helper reads a signed 32-bit control at owner `+0xa7c` and local longitudinal
velocity at `+0xa44`. It first converts the control to float32 and normalizes its
magnitude with the executable's float32 approximation to `1/127`:

```text
magnitude = float32(abs(float32(raw_control)) × float32(0.007874016))
blend = clamp(float32(abs(speed) × float32(0.022369863)), 0, 1)
shaped = float32((1 - blend) × magnitude +
                 (1 - (1 - blend)) × magnitude²)
result = min(shaped, 1)
if raw_control < 0: result = -result
```

The implementation preserves the expanded subtraction expression used by the
original, plus its storage boundaries. It does not substitute exact decimal
coefficients. Forward and reverse speeds share the same blend because speed is
absolute. The signed result is dimensionless; the speed input must be supplied
in original native units, whose upstream production remains part of the driving
investigation.

At control 63 and speed zero, the magnitude is approximately 0.496063. At a speed
that saturates the blend, the response becomes approximately 0.246078, its square.
Intermediate speeds interpolate between those values. Full control 127 remains
1 across speeds. This reduces sensitivity to partial input without reducing
full lock. The following tire update multiplies this result by an independently
stored steering parameter; this helper alone does not produce wheel angles.

## Verification and limits

```powershell
python -m tools.steering_response_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
python -m unittest tests.test_steering_response
python -m tools.native_steering_response_compare build/native-check/mco_steering_response_compare.exe
```

The bounded Windows oracle executes the complete original function without
substituted calls, checks the result and verifies the entire owner image remains
unchanged. Its corpus includes every signed eight-bit control value, int32
extremes, either speed sign, zero speed and values on either side of blend
saturation. Input validation is authored: the API rejects values outside int32
or finite float32 range rather than emulating invalid memory/input behavior.
All 2,064 original-function cases match exactly. The C++ port matches all 2,064
Python corpus cases exactly, with native unit checks and Windows/Linux CI
comparison. Local verification was on Windows.

Recovering this function does not establish input smoothing, controller dead
zones, maximum steering angle, left/right wheel geometry, rear steering, tire
slip or the full tire-force update. Those consumers and producers remain required.
