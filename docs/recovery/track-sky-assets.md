# Track sky resource setup

`Assets.load_sky_resources` reads the track's `sky.fsh` and applies the four
eight-pointer tables selected by the native night and wet flags in
`0x494070`. It preserves the exact native order, optional strings, and the
null final dry-day entry. The first four positions are primary sky resources;
the last four hold fixed lookup images or an indexed cloud-name pattern.

`0x4940f0` samples each available fixed lookup image into a 26×26 RGBA table.
The native step is binary32 `0.03846154` (`1/26` approximately): it multiplies
that step by the source width/height, scales each output coordinate, rounds to
the nearest integer, and clamps to the last valid source coordinate. The
adapter reproduces this bounded conversion and returns a 2,704-byte grid per
found lookup image. The indexed `%d` pattern at table position six generates
cloud names from index zero up to the caller-supplied count. As in the native
loop, the first missing cloud ends the consecutive sequence.

Validation against the adjacent installed game data decoded all 27 `sky.fsh`
archives. Fixed resource availability differs by track: the indexed cloud
sequence contains zero to eight consecutive images, with 23 tracks containing
at least one. Synthetic tests cover all four tables, exact sample scaling,
optional and null entries, cloud expansion and early termination, and
case-insensitive asset lookup. This is not an original-execution comparison.

This translation does not implement the Direct3D texture upload flags and
dimension tiers, global render-state writes, the caller's current cloud count
source, or sky rendering. `cloud_count` and `clouds_enabled` therefore remain
explicit caller inputs.

The procedural material kernel `0x4943f0` is only partially recovered. Its
deterministic 25×25 cell index table is now available through
`client.sky.sky_material_triangle_indices`; the original writes each row at a
`0x138`-byte stride, leaving `0x70` bytes after its 50 indices. The full native
buffer matches under the bounded original-execution comparison. The random
height generation and signed-square-root normalization are now translated and
compared at four parameter sets: 2,704 raw values and 2,704 normalized values
per stage, with exact raw floats and zero observed normalization error. The
random field is stored transposed (`column * 26 + row`). The native 20-pass,
in-place weighted 5×5 smoothing stage is now translated too; the same four
parameter sets compare all 2,704 values after smoothing with zero observed
error. Color packing and mesh-vertex updates remain untranslated. The shared
generator at `0x6f0fa0` is separately translated and compared across 1,024
states.

Evidence on `mcity.exe` SHA-256
`28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164`, Ghidra
12.1.4, profile digest
`3de5374fadd78e0d56219c4afc6b4f2efac7101ff92b72faf375fb0070bbc896`:

- Mode selection `0x494070`: `ev_345cfc1fa1547dd0e61d1498fb8505bb0ba972500a1e16d7dbe3cf730c3bb208`
- Sky resource loader and sampler `0x4940f0`: `ev_222ad7ba581e2c50e2647321e6ca0d286c5801f41f622e4eb15816513d944f5f`
- Pointer table bytes `0x891538..0x8915b7`: `ev_8b4fbdd664a0315049ce2fd0ff2083a14ac1ca4a816f5c1a3cbb8f52d936facc`
- Resource name pool bytes `0x8915c8..0x8916a7`: `ev_747c84b7683fa56b6c3771effe0154a7491b5eb896c0e5904529fe2bdf69e901`
- Exact SHPI name lookup `0x6c4080`: `ev_2a2616b7045e5fc4a9359081c786a597d21ccc87ec4a689191788be9a1f45eaa`
- Texture-table preparation `0x58a320`: `ev_eb63a53ca56e8266dff1c5d1c461e21818dd892486ff2fa60fab3985bee7893e`
- Indexed cloud format helper `0x699330`: `ev_b4a497760ae553c4c2fdf04747ca8ab3f960387c714af40ddd3fe95d6b1a6709`
- Integer clamp helper `0x6f1380`: `ev_7be2f31f8590766654160b7b92edb80f9d6d801c6d79d659eac94b924c1ba564`
- Procedural sky-material kernel `0x4943f0`: `ev_9de9d6afa83b7c0997de55c52f19572932b4d8059d0ad358066f78ff80844c92`
- Shared random generator `0x6f0fa0`: `ev_1a069217dbc28f2f1f5ade3b367ef667595ba5f70dd491c621a1b5ea1326a625`

The staged original comparison for the raw, normalized, and smoothed 26×26
local buffers is reproducible with `python -m tools.sky_material_grid_oracle
"/path/to/mcity.exe"`. It stops the original x86 routine at its corresponding
instruction boundaries before neighborhood smoothing.
