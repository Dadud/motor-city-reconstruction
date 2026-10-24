# Render polygon clipping

`0x475de0` is the renderer's triangle-to-polygon clipping routine. The bounded
translation in `client/render_polygon_clip.py` matches the near-W crossing,
the four isolated screen-edge passes, and one composed path: near-W followed
by upper-Y. In the composed path, a triangle first becomes a four-vertex
polygon at the W plane, then the upper-Y pass preserves the native vertex order
and adds any required second-plane intersections.

The near-W plus upper-Y path matches 512 calls against the installed
`mcity.exe`, including callback triangle count and all eight words of each
draw-trifan vertex. The one-plane paths and all-three-shared-near rejection
have separate native comparison corpora documented in the function review.

Other multi-plane combinations, initialization effects outside the supplied
records and bounds, and actual device rendering remain unrecovered.
