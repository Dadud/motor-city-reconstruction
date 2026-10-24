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
callback triangle count and all eight words of every output vertex. The
independent `0x02` depth flag is preserved as an inert mask/outcode bit; a
separate 64-call corpus confirms that depth-only calls emit the unchanged
triangle records. Mixed depth-flag plus clipping-plane combinations remain
outside this comparison contract. `0x474ee0` quad dispatch and actual device
rendering remain separate.

Caller setup effects outside the supplied records and bounds, and actual device
rendering remain unrecovered.

REA pseudocode Evidence: `ev_eaa44efee23196f7c1756dbb606ec8c7a42bd2a5be749d09ed517c3edfcaf65d`;
assembly Evidence: `ev_ac111242473578f4549776df99ea4212e51bfa7d51c7e81f6782d165955beedc`.
