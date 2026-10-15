# Complete numeric service and parking brake update

The authored Python/C++ `update_brake_forces` reconstructs the complete numeric
entry-to-return behavior of original `0x538960`, extending the previously
verified [thermal prefix](brake-thermal.md). It returns updated temperature,
countdown, per-wheel brake force, longitudinal force, spin adjustment and parking
ramp, plus ordered component-wear and controller-call records.

Target: x86 `mcity.exe`, SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA evidence for the enclosing routine:
`ev_37d3f01d4022f494ae7b8ea87b92ac5236f20843089b5167f101248bb4487b92`.
Fade: `ev_37809cda16227b622d90eaede3946ae095c9a2bb7994c39b8edcd7c8d976817e`;
quality: `ev_40dd7cf94b8acba699ae0ebaaa950623f0464e6e36ce46ca37496825cfab677c`;
wear dispatch: `ev_495ecf8fd8ed65113fa271bef1482b67ea6786fedf24ec75c0fe29b01875864c`;
controller no-op: `ev_03cc98fc85c3e37cfc637b66f8b489ccb217d9a65d05072b5702e76c522d8c73`.

## Sequence and supplied inputs

Thermal initialization runs first using the previous four brake forces and
current wheel spins/scales. Subsequent forces use the updated axle temperature.
Input and component producers remain supplied observations: service/parking
controls, quality, component codes, gate parameters, inertia terms, drive factor,
pitch and an auxiliary flag. Public APIs expose typed values rather than offsets.
The original quality helper simply reads the front/rear owner fields; it does
not look up a part or normalize the supplied value in this routine.

For service control `c`, axle quality `q`, temperature fade `f`, and cold-material
factor `k`, compute stored float32 strength:

```text
strength = (1 - min(q,0.5)) × f × k × c
```

Material code 3 below temperature 160 uses float32 0.8 for `k`; other cases use
1. Fade is 1 below the temperature limit, declines over the next 50 units, and
has a floor of 0.5. Above the limit, each wheel emits the original wear amount
`float32((temperature-limit) × float32(2.6041666e-6))`. These are observations of
numeric behavior; physical temperature/force units remain to be confirmed.

## Service torque and low-speed holding

With axle radius `r=diameter/2`, material multiplier is `0→0.85,1→0.9,2→0.95`,
otherwise 1. Nominal torque uses:

```text
capacity = material × r² × float32(π) × float32(16.310127) × 2500 × strength
```

Rear service torque additionally uses the supplied rear distribution. Construction
code 1 multiplies capacity by float32 0.98; its special component/vehicle branch
also multiplies by float32 0.8. Derived inertia is the stored value
`drive_factor × inertia_multiplier × 0.5 + inertia_addend`.

Above absolute body speed 1, absolute wheel spin below float32 0.05 reduces
torque by the smaller of absolute inertia times previous spin adjustment and
half capacity. Through body speed 1, pitch cosine, mass, normal load, spin scale
and strength determine a separate holding torque. Front and rear expressions
retain their original absolute-value and maximum ordering; they are not replaced
with a shared guessed friction rule.

## Parking, gates and spin limits

Rear parking/auxiliary mode uses full material torque, independent of service
strength and rear service distribution. It uses the base inertia addend and
chooses torque sign from projected wheel speed. Parking ramp adds 4 per rear
wheel and caps at 64, so a starting value 60 reaches 64 within one call.

An enabled axle gate can suppress a wheel at control angle at most float32 −0.4.
Suppression propagates to that axle's partner as the four wheels are processed.
It does not roll back a preceding wheel's already-written adjustment or force.
This asymmetric call ordering is covered explicitly by comparisons and tests.

Candidate spin adjustment is limited by absolute stored
`spin × 32 + previous_adjustment`, then limited again to oppose the spin without
crossing its zero-stop term. The final adjustment adds half the candidate for an
ungated axle and one quarter for an enabled gated wheel. Zero normal load skips
longitudinal-force modification. Otherwise the brake-force magnitude opposes
projected motion. Through body speed 1 the stored force is replaced by:

```text
brake_force = -projected_speed × mass × 8
```

For projected speed 0.5 and mass 1500, that low-speed value is −6000. It is still
subject to the axle gate and load conditions before affecting longitudinal force.

## External effects and verification

The original controller entry `0x41bd30` is a no-op return in this executable.
Its calls execute directly in the oracle and are retained as ordered observations
by the authored API. They do not establish working force feedback.
Wear goes through actual `0x5398d0` to component operation 5 for front wheels and
6 for rear wheels. The component-update boundary `0x591500` is supplied and
recorded; its health/event consumer and possible changes to later observations
remain external. No replacement hardware or component side effects are invented.

```powershell
python -m tools.brake_forces_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
python -m tools.native_brake_forces_compare build/native-check/mco_brake_forces_compare.exe
python -m unittest tests.test_brake_forces
```

All 376 complete-function scenarios pass. The oracle executes actual original
countdown, cooling, fade, quality, world-selector, trigonometry, wear-dispatch and
controller helpers; only component effect delivery is substituted. Every other
owner/configuration byte and the ordered effect calls are checked. Cases include
all represented materials, construction modes, high-temperature wear, service
and parking combinations, forward/reverse and speed boundaries, auxiliary-only
mode, mixed axle gates and adjacent spin thresholds.

Maximum original comparison error is `0.0001220703125` under tolerance
`max(0.0005, abs(original) × 3e-7)`. The native port matches its Python corpus
exactly. Invalid denominators and parking ramps outside `[0,64]` are rejected by
the authored API, without claiming original malformed-input handling.

Authentic component/input production, component wear/event delivery, downstream
wheel-spin/force integration and original-client braking traces remain required
before the complete game can claim faithful braking acceptance.

## Connection to the vehicle tick

[`DrivingBrakes`](../driving-pipeline.md#brakes-bound-into-the-vehicle-tick)
now connects these calculations to controls, engine flags, current wheel loads,
spin adjustment and subsequent tire/spin stages. The numeric API's `drive_factor`
is the selected table value: the original reads owner
`+0x1870 + selected_gear_byte*4`. Earlier isolated fixtures used gear 2 and
populated `+0x1878`. The integrated adapter requires the table and selects it
using current `+0xa69`. Authentic vehicle/gear preparation must produce it.

Python and C++ results now also retain one interleaved sequence of wear and
controller observations. The existing separate event arrays remain available.
All 376 original comparisons check the combined order; 376 native/Python
comparisons include kind, slot and value. Integration delivers this sequence
after the numeric stage; component mutations inside the original wheel loop
remain unverified.
