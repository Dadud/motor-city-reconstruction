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
`0x482700`, and actual device callback effects remain outside this recovery.
Evidence for the parent decompilation is REA Evidence
`ev_053cde75d143d6250566504cc8c474ecf3c2ca79788e69904de740d7a5cf63c3`.
