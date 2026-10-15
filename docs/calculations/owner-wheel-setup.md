# Wheel initialization and stance

Python `client/owner_wheel_setup.py` and C++ `native/src/owner_wheel_setup.cpp`
translate complete original functions `0x53b8a0` and `0x53b3c0` for finite,
explicit startup observations. Original executable SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
REA evidence: `ev_5eae717fe32ba2ccfdd3d26a9c6b879359b4322d13f59cdd1a818ea72d56676a`
and `ev_6aba179ce6a45346562f85d1a0ee39750051d79bdfaf90c3566751da5da99a98`.

Inputs are a finalized `0x820`-byte mechanical configuration and a `0x2000`-byte
owner observation. Radii at `0x18ec/0x18f0`, half height at `0xd0`, and wheel marker
positions at `0x18c4/0x18c8` must already be supplied in original model units
(metres in the recovered dimensional calculations). The assembly assertion is
caller responsibility, not proof that arbitrary bytes came from real assembly.
These byte-image adapters are internal research interfaces, not a stable mod API.

The initializer prepares four consecutive wheel records, quarter-mass loads,
inertias and reciprocals, brake allocation, flags and positions. A wheel's spin
inertia uses stored float32 `radius * radius * mass * 0.5`. Missing component mass
state selects the original 15-unit mass fallback. Transverse inertia adds
`width_metres² * float32(1/12)`; reciprocal evaluation retains the original wider
intermediate before storage. Width converts from configuration millimetres.

The rear width scale divides by the **front** tire-template width. All-zero
steering flags enable the rear pair. These unusual original rules are preserved.
Stance first adjusts each radius by `max(radius - float32(0.37), 0)`, computes the
nonpositive front/rear differences, and updates the observed chassis/wheel marker
positions. Intermediate float32 stores and unaffected owner bytes are retained.

Verification on Windows: complete original execution, no substituted callees,
all owner bytes exact in 56 wheel-setup cases and 56 standalone stance cases.
Sixteen cases use finalized configurations from stock cars 101–108 with explicitly
authored prior geometry; they do not verify real model startup. Forty authored
whole-image cases also match the C++ implementation exactly.

```sh
python -m tools.owner_wheel_setup_oracle /path/to/mcity.exe --database /path/to/Online.mdb
python -m tools.native_owner_wheel_setup_compare /path/to/mco_owner_wheel_setup_compare
```

Model selection/scaling/centering, projected area, complete `0x53a1f0`, contacts
and the integrated driving flow remain open. Do not manufacture these inputs
from prototype handling or assume newly computed levers replace prior state in
the original call order.
