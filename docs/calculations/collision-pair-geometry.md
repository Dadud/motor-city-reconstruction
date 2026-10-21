# Oriented-box point tests in `0x45af30`

`client.collision_pair_geometry` and `mco::collision_pair_geometry` now
translate all three bounded oriented-box point helpers called by the pair
routine `0x45af30`:

- `0x45b8e0` projects a target-local point into the owner basis, applies
  inclusive owner extents, then publishes the target-space world point and
  normalized target-basis direction on a hit.
- `0x45bb70` projects an owner-local point into the target basis, applies
  inclusive target extents, then publishes the owner-space world point and
  normalized inverse owner-basis direction on a hit.
- `0x45be10` performs the same owner-to-target point test and publishes the
  owner-space world point, without updating the direction scratch.

The original helper reads matrix and center-projection scratch prepared by its
caller. The comparison harness derives each helper's scratch from explicit box
records, then executes the original bodies. Each helper matches 192 direct
original calls, including 108 hits for both owner-to-target helpers and 106 for
`0x45b8e0`; maximum original/Python float difference is `3.814697265625e-6`.
The native port matches Python across the two corpora with maximum absolute
error `4.9121094747306415e-8`.

```powershell
python -m tools.collision_pair_geometry_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 192
python -m tools.collision_pair_geometry_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --reverse --cases 192
python -m tools.native_collision_pair_geometry_compare build/recovered-collision-pair/Release/mco_collision_pair_geometry_compare.exe
python -m tools.native_collision_pair_reverse_compare build/recovered-collision-pair/Release/mco_collision_pair_reverse_compare.exe
```

These three geometric leaves do not complete `0x45af30`. Its 32-step sample
order, per-object gates, paired contact writes, impulse delivery, and coupled
position/orientation response remain open. The tests supply caller-prepared
transform scratch and synthetic boxes; they do not establish live collision
behavior or complete game source.

Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Original function Evidence: `0x45b8e0` `ev_26113124fa0ff4884dea8c874ee9f2b2bad4eba3092f7d0b11a3bf056c17cf97`,
`0x45bb70` `ev_47af7817d94130338a593452cec9ef05af2846d7da3b1e202f1af00d698eb9e1`,
and `0x45be10` `ev_7c74d135bbf27cd454c1f44c8f4000b78c260839b54c97651aaad864ddb73f8e`.
Caller context Evidence: `ev_d07c6168165f0bef8d76f4b3aec6b75e67eb1682d94daf5a5a4b9c263e650fde`.
