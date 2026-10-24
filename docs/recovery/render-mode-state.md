# Renderer mode cache state

The shared helper at `0x6f1a30` replaces the render-mode word at `0x00b368cc`
and returns its previous value. A zero requested mode also invalidates the cache
word at `0x008c89f0` by writing `0xffffffff`; nonzero modes leave that second
word unchanged. Its callers include the track mesh builders at `0x495c00` and
`0x495f50`, as well as many other renderer and resource routines.

`client/render_state.py::replace_render_mode` exposes those globals as explicit
state inputs and outputs. It matched 512 direct calls against the installed
client, comparing the return value and both global words exactly. This recovers
one state primitive; callback selection and Direct3D dispatch in `0x6f28f0` and
full track-mesh construction remain to be translated.

REA function dossier: `ev_ac4d4f3f089b872a82453f4ec24eb1384716cc266b1354301fce15a4471f9910`.
