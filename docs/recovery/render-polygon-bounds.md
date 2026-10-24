# Render polygon bounds

`0x478610` scans a polygon's 32-byte point records, takes X/Y from the first two
binary32 values, merges the header's X extrema, and writes optional minimum-X,
minimum-Y, width and height outputs. A null polygon and empty point list follow the
original sentinel-to-zero behavior. Output pointers can independently be null.

`client/render_geometry.py::extract_render_polygon_bounds` translates the
helper and preserves the order of optional writes, including aliased output
buffers. Five hundred twelve randomized direct calls matched all requested
output words against the installed binary, including null/empty inputs and all
output masks. The enclosing UI draw path at `0x47f4a0` still has resource,
object, and device dependencies that are not part of this helper translation.

The Ghidra dossier is REA Evidence
`ev_75a1e6bf5d1ce7f93a6655150e053e26b8ab606410f8e24995599e56a945e858`.
