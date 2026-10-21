# Assembled engine curves

The Python research runtime reproduces the ordinary unboosted engine curve
finalizer, including its actual cylinder solver. Eight installed stock engines
(vehicle IDs 101–108) match the original complete 2,080-byte configuration exactly.
The special carburetor-kind-six branch is also reconstructed: each of those eight
engine configurations, modified only at the carburetor-kind field, matches the
original complete output and both solver inputs byte-for-byte; five additional
capacity values on vehicle 101 cover the initial-capacity clamp and the rerun
capacity ceiling. This is an engine
producer; complete car assembly and native driving remain open. Boost and
additional induction parts are still unsupported.

## Evidence and verification

Source: externally supplied `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA/Ghidra 12.1.4 dossiers identify these original functions:

| Function | Behavior | Evidence |
|---|---|---|
| `0x46d1d0` | Builder, solver calls and curve finalization | `ev_e8053db6582f9a26450eff04fd46d5f7e9f130e9422288ab81fab7a61caf3e92` |
| `0x54c980` | Exhaust contribution | `ev_892ebe39bb79353e12efda52d71e404eb08cb7539dc919ee9f433133aa373f17` |
| `0x54c650` | Electrical limits | `ev_0b22af02b2d7ad29c68cfa4bba11014485be05933f411a0dfaf47fbf19a8c322` |
| `0x54c1b0` | Valve RPM limit | `ev_76df93e2226c9765ad068a6693d0d0817d7105c8cea7fff4047e800b645d0a80` |
| `0x549fe0` | Power peak scan | `ev_c8e7afe1851ab92c4fe2834dbcdb9bd0cdbeb53498566b24c71e14c427d799f1` |
| `0x54b1a0` | Carburetor capacity requirement | `ev_8d56761243b8c6833687f507364571b199be0642c0f8ef4a5c8fc567a732c627` |

The finalizer's carburetor-six branch is independently visible in Ghidra
Evidence `ev_f54179b58dee485f395481712d72b6f411e0c6db8174667e15ca21f042d3070f`.

Comparisons use bounded x86 emulation with x87 control word `0x27f`, on Windows.
The eight stock cases execute the full original finalizer and solver without
substituted callees. A further 35 branch cases substitute only cylinder solver
outputs with authored curves: all configuration bytes and every solver input
record match, including two capacity reruns. These are CPU comparisons, not
original-client runtime traces. Private original data is not distributed.

```powershell
python -m tools.engine_curve_oracle '<game>/mcity.exe' '<game>/data/db/Online.mdb' --vehicles 101 102 103 104 105 106 107 108
python tools/verify_special_carburetor_curve.py '<game>/mcity.exe' '<game>/data/db/Online.mdb'
python -m tools.engine_curve_tail_oracle '<game>/mcity.exe' '<game>/data/db/Online.mdb'
python -m tools.inspect_stock_engine '<game>/data/db/Online.mdb' '<game>/mcity.exe' --vehicle 101
```

## Inputs and order

Selected catalogue engine components supply bore/stroke in metres, cylinder count,
compression, valve sizes in millimetres, cam timing/lift, flow-template selection,
intake/exhaust modes, carburetor capacity and electrical/valve limits. Flow
templates remain external in the executable. The finalizer converts these into
the existing [cylinder solver](cylinder-cycle.md)'s 1,004-byte record.

It converts nineteen torque samples at 2,000–11,000 RPM to slots 4–22 of a
25-point curve, using the original float32 multiplier `1.3558`. The likely physical
interpretation is torque conversion, but that multiplier is retained literally;
the resulting field is not verified wheel horsepower.

Low compression below six adds a penalty, with `d = compression - 6`:

```text
compression_penalty = clamp(d × .0675 - d² × .005, -.2, 0)
small_carb_penalty  = clamp((capacity - 300) × .0015, -.3, 0)
torque_factor      = 1 + compression_penalty + small_carb_penalty
```

The carburetor penalty applies only below capacity 300. Float32 constants, stores
and operation order matter. The source keeps intermediates wider where the x87
does; replacing all operations with float32 arithmetic changes results.

The first converted knot supplies power-derived 1,000 and 1,500 RPM values.
Exhaust, electrical and valve corrections run in that order, before final RPM
selection. Electrical capability checks both required power and RPM: one
insufficiency multiplies the curve by `.95`; both use `.85`, not `.95²`.
Above the valve limit, each knot is multiplied by
`(valve_limit / (sample_RPM + 500))²`.

Idle is interpolated at a torque threshold of 35% of peak, clamped to 90–180.
The resulting RPM is rounded, quantized down to 25 RPM, clamped to 500–3,000,
then increased by 150. Maximum RPM comes from the last minimum of the solver's
pressure series; higher curve entries are cleared. Ties therefore matter.

An oversized carburetor can trigger another solver call. The original then
scales the already corrected curve by the capacity ratio instead of rebuilding
it from the second torque series. The reconstruction retains this behavior.
The final scalar copied from the solver is a maximum of another native series;
it must not be mislabeled as peak power.

## Worked stock result and limits

Vehicle 101 yields idle **1,100 RPM**, maximum **6,500 RPM**, and a largest
converted torque sample of **156.54234313964844**. All configuration bytes match
the original call, not just these three values. Vehicle 106 yields 925 RPM,
7,000 RPM and 414.23358154296875 respectively.

The stock selector uses first matching supported components with authored zero
wear/damage. It does not implement the complete assembly dispatch or certify
modified inventory. Group quality, remaining components, whole-car mass,
geometry and owner startup remain separate requirements. The curve implementation
is currently Python; a C++ port is still required. Invalid curves without a safe
idle crossing fail explicitly rather than reproducing the original unsafe scan.
