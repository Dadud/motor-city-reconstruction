# Oriented-box point test `0x45b8e0`

`client.collision_pair_geometry.oriented_box_point_test` and
`mco::oriented_box_point_test` translate the complete bounded helper called by
the pair-collision routine `0x45af30`. Given owner and target oriented boxes
plus a normalized target-local point, the helper projects that point into the
owner basis, applies inclusive half-extent bounds, and on a hit publishes the
target-space world point and normalized target-basis direction.

The original helper reads matrix and center-projection scratch prepared by its
caller. The comparison harness derives that scratch from the explicit box
records, then executes the original `0x45b8e0` body. Across 192 cases (106 hits),
the Python translation matches the original hit/reject decision and compared
outputs with maximum absolute float difference `3.814697265625e-6`. The native
port matches Python over the same corpus with maximum absolute error
`4.9975586335904154e-8`.

```powershell
python -m tools.collision_pair_geometry_oracle "C:/Program Files (x86)/EA Games/Motor City Online/mcity.exe" --cases 192
python -m tools.native_collision_pair_geometry_compare build/recovered-collision-pair/Release/mco_collision_pair_geometry_compare.exe
```

This recovers one geometric primitive; it does not complete `0x45af30`. The
other two oriented-box tests, 32-step sample order, per-object gates, paired
contact writes and position/orientation response remain open. The test supplies
the caller-prepared transform scratch and uses synthetic boxes; it does not
establish live collision behavior or complete game source.

Target SHA-256:
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`.
Original function Evidence: `ev_26113124fa0ff4884dea8c874ee9f2b2bad4eba3092f7d0b11a3bf056c17cf97`.
Caller context Evidence: `ev_d07c6168165f0bef8d76f4b3aec6b75e67eb1682d94daf5a5a4b9c263e650fde`.
