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

Other multi-plane combinations, initialization effects outside the supplied
records and bounds, and actual device rendering remain unrecovered.
