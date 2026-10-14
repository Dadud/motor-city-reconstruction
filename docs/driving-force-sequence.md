# Shared-state force handoff comparison

`tools/driving_force_sequence_oracle.py` compares six recovered stages using a
single preserved owner/configuration image, in their observed relative order:

1. Tire update `0x53ecf0`.
2. Wheel-force/spin correction `0x53e130`.
3. Wheel-spin integration `0x5400b0`.
4. Combined-slip limiting `0x53fb30`.
5. Conditional force-orientation consumer `0x540520`.
6. Body moments `0x540710`, including `0x540600`.

The comparison does not execute the original caller or reproduce its conditional
dispatch. It deliberately runs the selected orientation branch with supplied
mode observations. Engine/brake force production, surface and contact
production, actual component effects, per-wheel caller force clearing,
linear/angular integration and scheduler are excluded. This is a handoff check,
not a complete original driving tick or a timestep specification.

The original oracle retains owner state across all stages and repeats that
sequence twice per scenario. The authored path feeds each stage's outputs into
the next rather than reinitializing from the original results. All 16 contact
masks, three speeds (`0.25,3,20`) and both steering directions produce 96
scenarios and 1,152 stage comparisons. After each stage it checks observed outputs
and every other owner/configuration byte for unexpected mutation.

Real original steering, trigonometry, curve, predicate, force correction,
cross-product, slip curve, loss observer and moment helpers execute. The predicate
interface's virtual operation 5 and component delivery methods `0x591500` and
`0x591180` are supplied. Receiver/argument checks include exactly four predicate
queries per tire stage and exact ordered component effect arguments. Wheel
scale, phase, slip ratio, secondary angle and limited forces carry forward
between stages and repeated calls. It does not access a host process or server.

```powershell
python -m tools.driving_force_sequence_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe"
```

Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
All stage comparisons pass with maximum absolute error
`0.000244140625`, under tolerance
`max(0.0005, abs(original) × 3e-7)`.

Inputs use authored response tables and supplied body/component/control state.
Original instruction bytes and raw owner captures remain private/external. The
next integration gate requires connecting the separately recovered
[vehicle controller](calculations/vehicle-update.md) and [scheduler](scheduler.md)
to authentic assembled-car inputs, followed by repeated original-client
acceleration, braking, cornering,
airborne and collision traces. This check cannot replace that acceptance gate.
