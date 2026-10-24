# Track cross-section geometry

`client/track_cross_section.py::build_track_cross_section` translates native function
`0x495240`, called directly by the track grid generator `0x495800`. The routine
projects an object's transform through the world basis, discards its vertical
component, normalizes the resulting direction (using +Z for a zero direction),
computes its turn angle, and derives a normalized perpendicular from the view
reference and world origin. It returns the direction point, the origin-offset
point, the perpendicular-offset point, and the turn angle.

The exact shipped executable was called 512 times with randomized finite
transforms, supplied globals, and positive and negative multi-turn offsets.
All 9 position floats stayed within `1.91e-6` absolute error and every angle
matched exactly. The in-place angle wrapper at `0x4b70f0` is separately
translated and exactly matches 256 direct native calls, including negative
turns, integer boundaries, and values above one.

The call depends on shared cross-product normalization `0x6f10d0`, separately
recovered in [normalized-cross.md](normalized-cross.md). REA function dossier:
`ev_683e3a85b3a542a68284aadadd85f600b761b0e7cb5f50a984abe8c7c05cb1cd`.

The shared `atan2_turns` in `client/matrix_math.py` now translates `0x6f1430`,
the x87 `FPATAN` helper used by this routine, collision terrain response, and
startup-record generation. It matched 1,024 direct original calls bit-for-bit
after the same binary32 result store used by callers. REA dossier:
`ev_337876610afd03208f28975030022110476923a7ba6b011aa6a85703204b1912`.

The same module also translates its larger caller `0x495800` as
`build_track_grid_strips`. It subtracts the object's vertical origin, recenters
the section around a 16-cell phase using the original truncating `__ftol`
conversion, then emits two 17-point strips in the native output-buffer order.
Across 256 original calls, all 8,704 strip points and the angle were compared;
the maximum position error was `2.14e-4` and every angle matched exactly.
The comparison includes finite randomized transforms and positive and negative
multi-turn offsets.

REA function dossier: `ev_032b6180253ad1117c37e229b63e759dcd86d09e35d615c5f3f5fad645ea0e56`.

The `0x4b70f0` wrapper maps values above one by subtracting their floor and
negative values by adding the ceiling of their magnitude; exactly `1.0` is
preserved. It maps negative integer turns to zero and keeps signed zero. REA
function dossier: `ev_f7e73576b4bacb1ef92dfdfb01b74b9384cf7d1ec506aa3e661ddfd0731805e7`.
