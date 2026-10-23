# Track cross-section geometry

`client/track_cross_section.py::build_track_cross_section` translates native function
`0x495240`, called directly by the track grid generator `0x495800`. The routine
projects an object's transform through the world basis, discards its vertical
component, normalizes the resulting direction (using +Z for a zero direction),
computes its turn angle, and derives a normalized perpendicular from the view
reference and world origin. It returns the direction point, the origin-offset
point, the perpendicular-offset point, and the turn angle.

The exact shipped executable was called 512 times with randomized finite
transforms and supplied globals. All 9 position floats stayed within
`1.91e-6` absolute error and every angle matched exactly. The verifier uses an
angle offset of zero, so the native wrap helper leaves the angle unchanged;
other wrapped-angle inputs are outside this comparison. The translated helper
supports offsets only when the resulting angle remains in `[0, 1]`.

The call depends on shared cross-product normalization `0x6f10d0`, separately
recovered in [normalized-cross.md](normalized-cross.md). REA function dossier:
`ev_683e3a85b3a542a68284aadadd85f600b761b0e7cb5f50a984abe8c7c05cb1cd`.

The same module also translates its larger caller `0x495800` as
`build_track_grid_strips`. It subtracts the object's vertical origin, recenters
the section around a 16-cell phase using the original truncating `__ftol`
conversion, then emits two 17-point strips in the native output-buffer order.
Across 256 original calls, all 8,704 strip points and the angle were compared;
the maximum position error was `2.45e-4` and every angle matched exactly.
The comparison uses finite randomized transforms, zero angle offset and the
native no-wrap path. Nonzero wrapped-angle cases remain unverified.

REA function dossier: `ev_032b6180253ad1117c37e229b63e759dcd86d09e35d615c5f3f5fad645ea0e56`.
