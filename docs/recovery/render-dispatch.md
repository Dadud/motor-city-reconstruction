# Render-mode callback dispatcher

The shared renderer routine at `0x6f28f0` filters requested mode flags against
capability globals, supplies default vertex stride/format values, selects a
primary callback from a 32-entry table and an optional secondary callback from
an 8-entry table, then validates draw count and pointers. Before dispatch it
updates the render-mode cache and draw-state globals. The primary callback gets
`(count, vertices, indices)`; the secondary gets `(count, indices)`.

`client/render_mode_dispatch.py::dispatch_render_mode` exposes the global words and
callback tables as `RenderDispatchState` and returns ordered callback events. The
installed client matched 512 direct calls exactly for the return word, all
mode/layout/draw-state globals, and the arguments observed by inert emulated
callbacks. Cases include both cache paths, flag combinations, both dispatch
callbacks, invalid draw arguments and randomized 32-bit state. This models the
dispatch boundary; callback implementation and GPU/device behavior remain
untranslated. The helper is called by track mesh functions `0x495c00` and
`0x495f50`, among many other renderer paths.

REA function dossier: `ev_61a4e6ccff1ff1e4617ca2e51c8aea0625a89b15ff52197f611e4758fe98a860`.

