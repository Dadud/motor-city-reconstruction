# Homogeneous vertex clip code

`0x6cb810` computes the one-byte code consumed by the renderer's clipping and
visibility callbacks. The helper compares signed XYZW words against six mutable
renderer limits, setting X/Y/W/Z bits and applying the original `0x3d` XOR when
W is negative. The six thresholds remain caller-supplied state; their runtime
producers and the broader clipping/draw pipeline are separate recovery work.

`client/render_clip_code.py::render_clip_code` reproduces the helper's ordered
branches. 512 deterministic cases, including threshold edges, negative W and
random signed 32-bit vertices, matched direct execution of the installed binary.

The Ghidra function dossier for the exact installed `mcity.exe` is REA Evidence
`ev_bc1bb75ed8e11be2f101f5d5a18a4e1a75d3d134896d0639c2818b1092b3ca19`.
