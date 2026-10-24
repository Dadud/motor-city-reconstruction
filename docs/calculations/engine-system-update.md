# Vehicle-path engine controller

`0x548260` is a separate engine controller called by `0x53c140` in the tilted
and low-support paths. It is not a motion-refresh routine. The controller's
previous `refresh_motion` placeholder is now named `engine_system_update` in
the Python and C++ vehicle dispatchers.

The recovered body shares its engine-mode dispatch with `0x545af0`, but has a
distinct prefix: it calls control update `0x540fd0`, caps the resulting
engagement value at `0.25`, then evaluates engine activation and vehicle flags.
Its active drivetrain path performs clutch setup, drive preparation, link and
load updates, accumulates the drive request, calls `0x548660` (a one-byte
`RET`), and continues with torque update, wheel distribution and force
application. The idle/start branches retain the original counter comparisons,
selector-indexed RPM fractions, limiter-derived fixed RPM, curve lookup, and
final link/load calls.

Python and C++ now implement the shared calculations through
`update_engine_system`; `update_engine` remains the separate `0x545af0` entry.
The direct comparison executes the original `0x548260` with explicit supplied
boundaries for the recovered control-update call and other effects, while the
original RPM and torque-curve routines run unchanged. It compares tracked engine
state, configuration bytes and ordered calls across **6,954 cases**, including
all six engagement values applied to the existing branch, counter, mutation and
curve corpus. MSVC/Python and C++/Python comparisons both report zero observed
numeric error. This does not certify real control acquisition, every child
effect, a complete car update or gameplay.

Evidence from the exact installed executable:

- SHA-256: `28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`
- REA decompilation/call-graph record: `ev_65c6b52d77b5116b8b714487deed906d81ed9282fe0ef56ec669b6f09d8f363a`
- Assembly check for `0x548660`: `0x548660: RET`

Reproduce the bounded original and native comparisons with:

```powershell
python -m tools.engine_update_oracle '<original-install>/mcity.exe' --vehicle-system
python -m tools.native_engine_update_compare build/native/mco_engine_update_compare --vehicle-system
```

The Windows and Linux native CI paths run both `0x545af0` and `0x548260` modes.
