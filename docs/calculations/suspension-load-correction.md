# Attitude and torque-dependent load correction

The complete `0x53e980` helper changes four normal-load accumulators after the
[acceleration-driven transfer](load-transfer.md). The authored implementation is
`client/suspension_load_correction.py`. Its old research filename described wheel
torque, but its outputs are normal loads, not wheel spin or a gearbox update.

Source `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA dossier: `ev_a4540e9362d8c616bf90fed86e0d838f7c5cfb6273bdc4d309909f8885968a7d`.

## Two correction stages

The outer gate requires absolute attitude no greater than 0.25 and nonzero
owner state at `+0xc08`. The API exposes that state as `enabled`; its full
gameplay meaning remains unresolved.

The first stage runs only when absolute speed exceeds 6. It derives weight
from `(mass - mass_offset) × float32(9.81)` and front/rear fractions from two
component parameters. Those parameters' physical meaning remains unresolved.
Their sum and fractions retain original float32 storage.

It applies turn-based sine of negative bank angle, adding the front contribution
to LF and subtracting it from RF; the corresponding rear contribution is added
to LR and subtracted from RR. A second turn-based sine of negative pitch angle
adds an axle contribution to each supported front wheel and subtracts the rear
contribution from each supported rear wheel. Front contributions are stored as
float32 before addition, while rear calculations retain intermediate precision
until writing the accumulator. All four loads are then clamped nonnegative.
Only supporting wheels receive these angle contributions.

The second stage is independent of that speed gate and of wheel support flags.
It runs when component mode `+0x6ec` is zero and owner flag bit 2 is clear:

```text
torque_correction = float32(abs(gear_factor × torque × rear_weight_parameter × 0.5 /
                               (rear_track × total_weight_parameter)))
LR = max(0, float32(LR + torque_correction))
RR = max(0, float32(RR - torque_correction))
```

The original selects `gear_factor` from component `+0x334 + gear_byte×4`; the API
takes the already selected value. Torque sign does not reverse the correction
because the helper takes its absolute value. Unsupported rear wheels can receive
this contribution. Moving the support test or speed test around the entire
helper would therefore change original behavior.

## Comparison and limits

```powershell
python -m tools.suspension_load_oracle 'C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe'
python -m unittest tests.test_suspension_load_correction
python -m tools.native_suspension_load_compare build/native-check/mco_suspension_load_compare.exe
```

The local Windows complete-function oracle passes 1,730 cases with zero maximum
stored-load difference. It executes the original sine helpers without substituted
calls, compares four loads and checks the full remaining owner/configuration
images for mutation. Cases include all support masks, exact attitude/speed gates,
either torque sign, component mode and flag gates, disabled owner state and zero
clamp crossings. Four unit tests cover these distinctions and invalid inputs.
The C++ port matches all 1,730 Python cases exactly; its native comparison runs
in Windows/Linux CI. Local verification was on Windows.

The comparison uses supplied component/state observations, not an assembled car
or a running race. Full meaning and production of enabled state, bank/pitch angles,
component weight parameters, gear factor and torque remain required. The API
rejects malformed or nonfinite observations and invalid dimensions; these input
rejections are authored safeguards.
