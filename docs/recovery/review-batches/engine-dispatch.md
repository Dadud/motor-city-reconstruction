# Engine dispatcher and consumer review batch

Reviewed on 2026-10-15 against the exact main executable SHA-256 recorded in
`engine-dispatch.json`. Six additive dispositions cover existing authored
Python/C++ implementations. They do not add six newly translated bodies, and do
not certify a complete engine or driving client. None duplicates the 43 legacy
reviews present at audit time.

| Original entry | Reviewed behavior | Fresh original comparison |
|---|---|---|
| `0x545af0` | Engine-mode/startup dispatcher | 1,159 cases |
| `0x548f00` | Adjacent 500-RPM torque-knot interpolation | Observed through dispatcher/torque/pipeline callers |
| `0x547120` | Full torque-update body | 1,094 cases |
| `0x546330` | Condition/gate body, working name `gear_link` | Part of 1,136 combined condition/thermal cases |
| `0x5464c0` | Thermal body, working name `drivetrain_loads` | Part of the same 1,136 cases |
| `0x546e70` | Driving RPM helper | 2,592 cases; no calls replaced |
| `0x548260` | Vehicle-path engine controller, including control prelude and engagement cap | 6,954 cases; actual RPM/curve children and explicit supplied side-effect boundaries |

The connected engine pipeline additionally passes **514 scenarios and 1,696
persistent ticks**, starting at the original dispatcher and retaining the real
torque, condition, thermal, curve, environment, RPM and CRT-power bodies. Those
ticks are corroborating integration evidence, not extra reviewed function
entries or a full vehicle simulation.

All five original commands completed successfully with zero reported numeric
error. Comparators check exact integer fields, unchanged remainder owner and
configuration bytes, and ordered child calls. Numeric checks have coded
tolerances; zero observed error is not a signed-zero/NaN bitwise guarantee.
Floating call arguments have separate tolerances. The curve helper is verified
through caller-observable stores and power, not an exhaustive standalone check
of its unstored x87 return value.

## Reproduce

Use the repository virtual environment, with Unicorn installed, and supply the
external original executable as the sole positional argument to each module:

```powershell
.venv/Scripts/python.exe -m tools.engine_update_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
.venv/Scripts/python.exe -m tools.engine_torque_update_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
.venv/Scripts/python.exe -m tools.drivetrain_links_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
.venv/Scripts/python.exe -m tools.driving_engine_rpm_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
.venv/Scripts/python.exe -m tools.engine_pipeline_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

The corresponding `tools.native_engine_update_compare`,
`tools.native_engine_torque_update_compare`, `tools.native_drivetrain_links_compare`,
`tools.native_driving_engine_rpm_compare`, and `tools.native_engine_pipeline_compare`
commands were run against their existing `build/msvc-check/mco_*_compare.exe`
runners. They pass the same respective counts with zero reported numeric error.
This audit did not perform a fresh native build or Linux run; the integration
lead must rebuild/check the current tree and retain cross-platform CI.

## Evidence and limits

The saved REA records' target digests and Evidence IDs were checked against the
declared hash. Their IDs appear in the JSON beside authored sources and
verification tools. Private records, pseudocode and executable bytes remain
outside this batch. The comparison harness independently checks the original
executable digest before loading it into bounded CPU emulation. It does not
launch the game entry point, host imports or network services.

Dispatcher setup/control, engagement input, wheel-drive/finalization, startup/
idle, interface/counter observations and delay/curve data remain supplied in
isolated dispatcher tests. The connected pipeline removes the torque and
condition/thermal substitutions but still supplies the other producers. Torque
tests supply pulse `0x4b7170`, boost `0x549580`, query `0x55cfc0`, limit
`0x54d250`, damage `0x5452c0` and effects `0x591180`/`0x591500` where called.
Mutation cases verify that later stages reread changed owner fields.

The authored APIs reject malformed, nonfinite, singular or out-of-envelope
inputs; matching those original failure modes is not claimed. API-accepted
ranges are wider than the finite comparison corpus. The physical identity and
units of condition/thermal fields remain inferred. Dispatcher names `gear_link`
and `drivetrain_loads` are compatibility names, not recovered gearbox/differential
semantics.

Remaining gates are authentic component/catalogue and control producers,
remaining child bodies, a fully initialized original car feeding the native
update, contact/force integration, original-client runtime traces and live race
verification. Older remaining-work paragraphs in individual calculation notes
predate later torque/dispatcher ports; the JSON dispositions and the connected
engine-pipeline note describe the bounded current status.
