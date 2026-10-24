# Render rectangle border path

`0x47faf0` has an early empty-rectangle gate and a filled branch that calls
`0x482700`. Its non-filled branch subtracts the renderer inset from width and
height, then calls `0x482610` four times in top, right, bottom, left order.
The four raw attributes advance cyclically across those edges.

`client/render_rectangle.py::plan_rectangle_border_edges` captures that
geometry and 32-bit signed arithmetic. `construct_rectangle_border` can feed
those edges through the translated segment constructor when the caller
provides the renderer clip bounds and untouched stack residue for each native
call. The segment constructor has 512 direct original comparisons. The
rectangle-level parent geometry is still based on static decompilation and
unit tests; its MFC/provider setup has not yet been bounded by a direct parent
comparison.

Provider/resource lookup and its side effects remain outside this recovery.
The filled rectangle routine `0x482700` is partly recovered:
`plan_filled_rectangle_vertices` builds
the TL, TR, BR, BL records, preserves each raw attribute and the three-word
tail at each vertex. `0x6cb810` overwrites only the low byte of the first tail
word with its clip code; the upper bytes and following words remain explicit
stack-residue inputs.

The full branch router in `0x474ee0` is translated in
`client/render_quad_dispatch.py`. Its 1,024-call direct-original corpus checks
the all-inside quad callback, shared-outcode rejection, both fan triangles,
canonical-NaN suppression, and the two calls into `0x475de0`. The oracle
captures every direct draw record plus each clip call's vertex order, packed
clip codes, and active mask. The clipper itself is a controlled stub for this
parent-only comparison; its ordered five-plane implementation has a separate
512-case original comparison in [polygon clipping](render-polygon-clip.md).
The older isolated all-inside and fan corpora remain in place. Actual GPU
effects and resource callbacks remain external.

REA decompilation Evidence: `ev_66df9863fec9d9a4b721f719e85227fe1c22253cbb9bdde2980d0a77fb001844`.
Focused pseudocode Evidence: `ev_2c0a78676f9b255779fca8cf1de72797c836f1ae8e8b6450a95f5cadec4c0203`.

The rectangle setup's `0x46abd0(0)` state reset is translated by
`select_rectangle_texture_state`. It preserves the cache-hit path and emits
the `THRASH_settexture(0)` callback event on a miss. Two hundred fifty-six
direct calls cover both cache states; nonzero texture-state selection and its
resource side effects are not included.

`client/render_polygon_clip.py` also models the first-plane empty result in
`0x475de0`: when all three polygon clip codes share active near-plane bit
`0x01`, the original returns `0xffffffff`. This sentinel matched 256 direct
native calls. For a triangle with exactly one vertex outside that plane, its
intersection interpolation and final `THRASH_drawtrifan` records are also
translated. A 1,024-case direct corpus matches callback counts and every
eight-word output vertex, including each outside-corner position and color
interpolation mode. The same implementation covers the isolated upper-Y
(`0x08`) and lower-Y (`0x04`) passes, with 512 direct comparisons each across
three outside-corner positions and color modes. The left-X (`0x10`) and
right-X (`0x20`) passes also match 512 native comparisons each across the same
domains. These single-plane checks are complemented by the ordered multi-plane
composition in clip_triangle_planes, which compares 512 inputs spanning all
31 nonempty subsets of the five clip planes. The global vertex setup writes
performed before the shared-plane return are not modeled; later passes remain
open.
