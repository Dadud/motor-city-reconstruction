# Renderer vertex descriptor query

The shared helper at `0x6f3090` uses render mode `8` when its optional mode
argument is zero, or temporarily sets the supplied mode and dispatches `0x10008`
otherwise. It calls `0x6f28f0` for one input vertex and copies four words from the
callback's stack result to four independently optional outputs. It restores the
previous mode only when the setter returned a nonzero prior value; this means a
zero prior mode leaves the temporary global in place.

`client/render_vertex_descriptor.py::query_render_vertex_descriptor` models the
mode setter and dispatcher as explicit dependencies and returns the four values
and selected output writes. With controlled native callback stubs, it matched 128
direct calls against the installed client, including all output masks, both
dispatch modes, zero/nonzero prior modes, final cache/mode state, and callback
counts. Callback implementations and actual Direct3D device effects remain
outside this wrapper translation.

REA dossier: `ev_4fe53d347652730b69f6b8a62cfd62190d408fa183195d051f8913e267117191`.
