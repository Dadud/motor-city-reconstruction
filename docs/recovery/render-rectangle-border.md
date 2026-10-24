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

The provider/resource lookup, its side effects, the filled rectangle routine
`0x482700` is now partly recovered: `plan_filled_rectangle_vertices` builds
the TL, TR, BR, BL records, preserves each raw attribute and the three-word
tail at each vertex. `0x6cb810` overwrites only the low byte of the first tail
word with its clip code; the upper bytes and following words remain explicit
stack-residue inputs. It does not model the initial renderer-state
reset (`0x46abd0`) or the subsequent four-vertex polygon dispatch (`0x474ee0`),
which performs clipping and callbacks.

The all-inside branch of `0x474ee0` is translated in
`client/render_quad_dispatch.py`. A 256-case direct comparison captures the
four records at the quad callback boundary, including depth adjustment,
fallback depth, raw attributes, untouched tail words, and canonical-NaN
inputs. The native binary dispatches those canonical-NaN records even though
the retained Ghidra pseudocode appears to reject them; the translation follows
the direct observation.

The same module translates the fan branch that emits vertices 0, 1, and 2
when only vertex 3 is outside. In 128 direct comparisons the triangle callback
payload and the canonical-NaN suppression matched. For this subregion check,
the oracle replaces the subsequent complementary-polygon clipper `0x475de0`
with a no-op so its behavior is not included in the claim. Other clipping
branches and actual device effects remain outside this recovery. Evidence for
the parent decompilation is REA Evidence
`ev_053cde75d143d6250566504cc8c474ecf3c2ca79788e69904de740d7a5cf63c3`.

The rectangle setup's `0x46abd0(0)` state reset is translated by
`select_rectangle_texture_state`. It preserves the cache-hit path and emits
the `THRASH_settexture(0)` callback event on a miss. Two hundred fifty-six
direct calls cover both cache states; nonzero texture-state selection and its
resource side effects are not included.
