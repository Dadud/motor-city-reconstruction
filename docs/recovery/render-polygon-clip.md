# Render polygon clipping

`0x475de0` is the renderer's triangle-to-polygon clipping routine. The bounded
translation in `client/render_polygon_clip.py` matches the near-W crossing,
the four isolated screen-edge passes, and one composed path: near-W followed
by upper-Y. In the composed path, a triangle first becomes a four-vertex
polygon at the W plane, then the upper-Y pass preserves the native vertex order
and adds any required second-plane intersections.

Near-W composition with upper-Y, lower-Y, left-X, and right-X each matches 512
calls against the installed `mcity.exe`. A three-plane near-W, upper-Y, left-X
path also matches 512 calls. Comparisons check callback triangle count and all
eight words of every draw-trifan vertex. The one-plane paths and all-three-
shared-near rejection have separate native comparison corpora documented in
the function review. These initial composition corpora use varied geometry,
but isolate one outside input vertex per plane before the generated vertices
exercise later passes.

`clip_triangle_planes` now translates the ordered five-plane pipeline for
near-W, upper/lower-Y, and left/right-X. A 512-call direct-original corpus
covers all 31 nonempty subsets of those planes, multiple outside input vertices,
and generated intersections consumed by later passes. Each call compares the
callback triangle count and all eight words of every output vertex. The native
caller supplies the active mask; enabled bits without matching outcodes are
outside this comparison contract. The independent far-depth outcode and
`0x474ee0` quad-dispatch branches remain separate.

Caller setup effects outside the supplied records and bounds, and actual device
rendering remain unrecovered.
