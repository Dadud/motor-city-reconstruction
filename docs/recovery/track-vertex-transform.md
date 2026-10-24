# Track mesh per-vertex transform

In `0x495c00`, the successful strip-build branch runs two 17-point loops. Each
point is multiplied by the 3×3 matrix at object offset `0x44`; the three
components are x87 dot products stored to local binary32 values. The adjacent
`0x495f50` mesh builder contains the same transform sequence.

`client/track_vertex_transform.py::transform_track_vertex` translates this
per-point operation. It matched 512 deterministic vectors bit-for-bit using
1,536 direct calls to the original `0x6f1140` dot-product helper. The remainder
of either mesh builder is still unimplemented: stateful descriptor creation in
`0x6f3090`, display-list traversal through `0x55e8f0`, and material/device draw
dispatch through `0x494e90`.

REA dossier for `0x495c00`:
`ev_dcc86e9d961638fd6f67dd5764628d275474b782a277931813db07e845e520d6`. The native
dot helper has separately retained evidence IDs in the function inventory.
