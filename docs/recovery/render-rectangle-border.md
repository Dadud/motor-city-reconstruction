# Render rectangle border path

`0x47faf0` has an early empty-rectangle gate and a filled branch that calls
`0x482700`. Its non-filled branch subtracts the renderer inset from width and
height, then calls `0x482610` four times in top, right, bottom, left order.
The four raw attributes advance cyclically across those edges.

`client/render_rectangle.py::plan_rectangle_border_edges` captures that
geometry and 32-bit signed arithmetic. `construct_rectangle_border` can feed
those edges through the translated segment constructor when the caller
provides the renderer clip bounds and untouched stack residue for each native
call. The segment constructor has 512 direct original comparisons. This
rectangle-level geometry is based on static decompilation and unit tests; the
parent routine has not yet been compared directly against the executable.

Provider/resource lookup and its side effects remain outside this recovery.
The filled rectangle routine `0x482700` is partly recovered:
`plan_filled_rectangle_vertices` builds
the TL, TR, BR, BL records, preserves each raw attribute and the three-word
tail at each vertex. `0x6cb810` overwrites only the low byte of the first tail
word with its clip code; the upper bytes and following words remain explicit
stack-residue inputs.

The all-inside branch of `0x474ee0` is translated in
`client/render_quad_dispatch.py`. A 256-case direct comparison captures the
four records at the quad callback boundary, including depth adjustment,
fallback depth, raw attributes, untouched tail words, and canonical-NaN
inputs. The native binary dispatches those canonical-NaN records even though
the retained Ghidra pseudocode appears to reject them; the translation follows
the direct observation.

The same module translates both trivial fan branches: vertices 0, 1, 2 when
vertex 3 is outside, and vertices 0, 2, 3 when vertex 1 is outside. In 256
direct comparisons of each branch, the triangle callback payload and
canonical-NaN suppression matched. For these subregion checks, the oracle
replaces the complementary polygon clipper `0x475de0` with a no-op so its
behavior is not included in the claim. Other clipping branches and actual
device effects remain outside this recovery. Evidence for
the parent decompilation is REA Evidence
`ev_053cde75d143d6250566504cc8c474ecf3c2ca79788e69904de740d7a5cf63c3`.

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
domains. These are separate single-plane checks; their composition and
multi-plane intersections have not been verified. The global
vertex setup writes performed before the
shared-plane return are not modeled; other clip planes, multi-plane
intersections, and later passes remain open.
