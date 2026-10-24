# Renderer viewport setup

`0x6cb610` installs the renderer's viewport bounds and two W-plane parameters used by
`0x6cb810` and `0x6cb970`. It stores the input origin, origin-plus-size edges,
the two W-plane parameters, reciprocal of the Z=0 W-plane value, reciprocal depth span, and the
related clip constants. It also clears one 32-bit field at offset `0x14` in each
of 100 records spaced 32 bytes apart.

`client/render_viewport.py::configure_render_viewport` translates those global
writes and the strided clear. 512 randomized viewport configurations matched
all captured float32 globals and all 100 record writes against direct execution
of the installed binary. The caller's viewport inputs and backing scratch table
are explicit; the higher-level device/window setup is still separate.

Its caller `0x5668c0` clamps a requested rectangle to configured surface
dimensions, then supplies W-plane values `10.0` and approximately
`0.0016666667`. They are retained by Z-plane role here instead of assuming the
usual near/far naming convention.

The complete Ghidra dossier is REA Evidence
`ev_b77b3876cf605d6f1bc6d5f1e3c18a18e345249e3d708c06a0af3441e2dd3402`.

The caller's alternate path also invokes `0x474d00`, which copies its four
rectangle edges into two renderer-global alias sets. `set_alternate_render_bounds`
preserves that exact mapping; the combined verifier compares all eight globals
against the original binary for each randomized viewport case. Its dossier is
REA Evidence `ev_f782911e63ddfa5e5226a75f797cf913ac34ecd726c75e06d23fb23fbb18c6ff`.
