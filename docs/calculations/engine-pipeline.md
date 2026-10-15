# Connected engine pipeline

The Python pipeline is also bound to the vehicle tick by
[`DrivingEngine`](../driving-pipeline.md#engine-bound-into-the-vehicle-tick).
That comparison now includes real input smoothing, load/environment producers
and tire forces, with explicitly supplied setup/clutch/wheel-drive and brake
boundaries. The C++ engine pipeline remains independently verified; a complete
native driving integration is still required.

`client/engine_pipeline.py` and `native/src/engine_pipeline.cpp` connect the
recovered engine dispatcher (`0x545af0`) to the complete torque update
(`0x547120`) and both condition/thermal routines (`0x546330`, `0x5464c0`).
They use one canonical owner state. This replaces isolated fixture handoffs with
the actual state relationships and update ordering established by the original
executable. It does not replace unrecovered producers with a handling model.

## Shared state and distinct records

Some recovered types use different names for the same original field. Other
similarly named fields are separate records and must never be copied together:

| Pipeline field | Original field | Connected consumers |
|---|---|---|
| `engagement` | owner `+0xb2c` | Dispatcher and torque/coupling |
| `thermal_engagement` | owner `+0xac8` | Condition/thermal routines |
| `rpm_state.rpm` | owner `+0xab4` | All four routines |
| `rpm_state.normalized_rpm` | owner `+0xabc` | All four routines |
| `rpm_state.longitudinal_speed` | owner `+0xa44` | RPM and thermal cooling |
| `auxiliary_temperature` | owner `+0xacc` | Torque deductions and thermal integration |
| `loss` | owner `+0xae0` | Thermal output and torque deduction |
| `boost_observation` | owner `+0xce8` | Boost eligibility and thermal source selection |
| `alternate_enabled` | owner `+0xa86` | Boost and thermal source selection |
| `engine_flags` | owner `+0xae4` | Dispatcher, torque and condition |

The two engagement records have independent values and producers. An external
damage consumer can change driveline engagement while a thermal child is
running; that write survives even though driveline engagement is outside the
thermal type. Conversely, changing thermal engagement never silently changes
the coupling value.

Catalogue aliases are also validated. The torque and thermal configuration
must agree on material index (`+0x4f4`), durability index (`+0x42c`), loss index
(`+0x4d8`), third-system flag (`+0x68c`), upgrade enable (`+0x6f0`) and the
shared threshold (`+0x3e0`). Conflicting fixture/configuration values are
rejected instead of allowing different children to read different catalogues.

## Ordering and synchronization

For the normal enabled driving branch with vehicle flags 4, the dispatcher
invokes these stages in their original order:

```
engine_setup       supplied
engine_control     supplied
gear_link          recovered complete condition body
drivetrain_loads   recovered complete thermal body
engagement_inputs  supplied
torque_update      recovered complete torque body, environment and RPM
wheel_drive        supplied
engine_finalize    supplied
```

Other dispatcher flag combinations take the already recovered startup/fixed-RPM
branches. In particular, the flags-6/7 path runs torque and then writes effective
torque 100 and recomputes curve torque/power. Flags 7 subsequently run the two
condition children. The pipeline preserves these overwrites; it does not choose
a more plausible ordering or retain an output the original overwrote.

At every child entry, the active recovered state's writes are copied into the
canonical owner. External callbacks receive that owner, and their binary32
writes are normalized before copying back into the active child. On return,
only the fields belonging to that child are imported. This preserves writes to
other fields while reproducing the child's subsequent rereads.

Each output records the complete ordered call sequence, including the top-level
dispatcher calls and nested torque/thermal calls. Domains distinguish, for
example, damage invoked by `gear_link` from damage invoked by `torque_update`.
The caller retains the resulting owner for the next tick. Advancing the original
counter or supplying new controls remains the caller's responsibility.

## Required external boundaries

The callback is mandatory; a missing producer must fail explicitly. The Python
callback receives `PipelineCall` and mutable `EnginePipelineState`; the native
callback receives their typed equivalents. Calls have domain, stage, optional
code and typed numeric arguments. Return values follow the recovered children:

| Boundary | Required result |
|---|---|
| Dispatcher interface/counter observations | Original integer result |
| Dispatcher setup/control/clutch/wheel/finalization stages | Explicit supplied state changes |
| Torque pulse | Numeric waveform result |
| Torque brake query / RPM limit | Original integer observation |
| Torque boost | Torque result plus binary32 observation increment |
| Damage and effect consumers | Explicit supplied state changes; result unused |

Python boost returns `(torque, increment)`. Native callbacks use
`TorqueStageResult.value` and `.boost_increment`. All remaining known numeric
children execute directly: inline torque interpolation, CRT powers, environment
correction, torque/coupling, RPM update and condition/thermal integration.
This interface is a research composition API, separate from the stable mod API.

## Original comparison

The original and optimized Windows native comparisons each pass **514 scenarios
and 1,696 persistent ticks with zero error**. Both check the complete nested call
sequence. Run:

```powershell
python -m tools.engine_pipeline_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m tools.native_engine_pipeline_compare build/native-check/mco_engine_pipeline_compare.exe
```

The comparison starts at original `0x545af0` and leaves `0x547120`, `0x546330`,
`0x5464c0`, the CRT powers, environment helper, curve helper and RPM helper
unchanged in emulated memory. Only the explicitly supplied boundaries above
are substituted. The verified original executable is an external read-only
input; execution is CPU-only and bounded, with no host game launch or services.

Scenarios retain owner bytes between three to five consecutive calls, rather
than recreating independent inputs each tick. They cover different dispatcher
flags, enabled state, throttle, both engagement records, thermal modes and
temperatures, bypass, third-system flags, boost and cross-subsystem callback
writes. Comparison checks the full owner/configuration image, stored numerics,
exact integer fields, nested call order and arguments. Native/Python comparison
uses the same persistent trajectories.

Evidence reused from complete original routines:

- Dispatcher: `ev_f4138fe586f7a644826c3fed0bf4ac2ff952ab9063efe9cdcc51b1623111253b`.
- Torque: `ev_287a64b85764bf6ac1fd3474ee9c2a7a25b31ff198369aedd2755021570487c8`.
- Condition: `ev_666ad5a328b851f0f2396a6ad75e7e1be3a9addcf69236ba4f3f29db0894d037`.
- Thermal: `ev_93f172b8530abd4d7631be96a4cd4d8c8d1f97bcfce2146070591d79fd4ce017`.

Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.

This establishes the connected recovered engine consumers and their storage
relationships. It does not establish the remaining control/clutch/wheel-drive
producers, complete force/contact integration, real car catalogue preparation,
original-client runtime traces or fan-server race compatibility.
